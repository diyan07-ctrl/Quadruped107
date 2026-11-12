"""Explicit non-actuating telemetry provider. Never fabricates sweep/fallback data."""
from .sensors import SensorManager, TWO_TOUCH_PROFILE


class PhysicalSensorProvider:
    def __init__(self, link, manager):
        self.link = link
        self.manager = manager
        self.last = None
        self.batch_seq = 0
        self.epoch = None
        self.telemetry_errors = None
        self.invalid_record = None

    def update(self):
        health = self.link.snapshot()
        epoch = (health['epoch'],self.manager.config.touch_profile,self.manager.config.touch_count,
                 health.get('sensorTouchCount'))
        if epoch != self.epoch:
            self.epoch = epoch
            self.last = None
            self.invalid_record = None
            self.manager.reset(f'uno-sensor:{epoch}')
        snapshot = health['telemetry']
        record = snapshot.get('record')
        errors=snapshot.get('errors',0)
        if self.manager.config.touch_profile==TWO_TOUCH_PROFILE:
            changed=(errors>0 if self.telemetry_errors is None else errors!=self.telemetry_errors)
            self.telemetry_errors=errors
            if changed:
                self.invalid_record=(epoch,record['seq']) if record else None
                self.manager.reset(f'uno-sensor:{epoch}')
                self.last=None
                return
        if (not health['connected'] or health.get('firmwareIdentity')!='caps_sensor2' or
            (self.manager.config.touch_profile==TWO_TOUCH_PROFILE and self.link.sensor_touch_count!=2) or
            (record and record['touch_mask'] & ~((1 << self.link.sensor_touch_count)-1)) or
            not record or not snapshot.get('acquisitionFreshnessKnown')):
            self.manager.reset(f'uno-sensor:{epoch}')
            self.last = None
            return
        key = (epoch, record['seq'])
        if key==self.invalid_record:
            return # A corrupt/duplicate packet cannot resurrect the preceding record.
        self.invalid_record=None
        if key == self.last:
            return  # Repeated polls must not relabel receive time or replay touches.
        self.last = key
        self.batch_seq += 1
        observations = [dict(id='urm37', kind='range', value=snapshot.get('distanceM'),
            valid=bool(snapshot.get('rangeValid')), age=snapshot['rangeAge'],
            error=None if snapshot.get('rangeValid') else 'Physical range invalid/unconfigured')]
        count=min(self.manager.config.touch_count,self.link.sensor_touch_count)
        for index, name in enumerate(self.manager.config.touch_ids[:count]):
            observations.append(dict(id='touch_'+name, kind='touch',
                value=bool(record['touch_mask'] & (1 << index)),
                valid=bool(snapshot.get('touchValid')), age=snapshot['touchAge'],
                error=None if snapshot.get('touchValid') else 'Physical touch invalid/unconfigured'))
        self.manager.ingest(dict(schema=1, seq=self.batch_seq, observations=observations),
                            session=f'uno-sensor:{epoch}')


def physical_manager(config=None, **kwargs):
    return SensorManager(config, source='physical_uno', **kwargs)
