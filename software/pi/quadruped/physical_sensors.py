"""Explicit non-actuating telemetry provider. Never fabricates sweep/fallback data."""
from .sensors import SensorManager, TOUCH_IDS


class PhysicalSensorProvider:
    def __init__(self, link, manager):
        self.link = link
        self.manager = manager
        self.last = None
        self.batch_seq = 0
        self.epoch = None

    def update(self):
        health = self.link.snapshot()
        epoch = health['epoch']
        if epoch != self.epoch:
            self.epoch = epoch
            self.last = None
            self.manager.reset(f'uno-sensor:{epoch}')
        snapshot = health['telemetry']
        record = snapshot.get('record')
        if (not health['connected'] or health.get('firmwareIdentity')!='caps_sensor2' or
            not record or not snapshot.get('acquisitionFreshnessKnown')):
            self.manager.reset(f'uno-sensor:{epoch}')
            self.last = None
            return
        key = (epoch, record['seq'])
        if key == self.last:
            return  # Repeated polls must not relabel receive time or replay touches.
        self.last = key
        self.batch_seq += 1
        observations = [dict(id='urm37', kind='range', value=snapshot.get('distanceM'),
            valid=bool(snapshot.get('rangeValid')), age=snapshot['rangeAge'],
            error=None if snapshot.get('rangeValid') else 'Physical range invalid/unconfigured')]
        for index, name in enumerate(TOUCH_IDS[:self.manager.config.touch_count]):
            observations.append(dict(id='touch_'+name, kind='touch',
                value=bool(record['touch_mask'] & (1 << index)),
                valid=bool(snapshot.get('touchValid')), age=snapshot['touchAge'],
                error=None if snapshot.get('touchValid') else 'Physical touch invalid/unconfigured'))
        self.manager.ingest(dict(schema=1, seq=self.batch_seq, observations=observations),
                            session=f'uno-sensor:{epoch}')


def physical_manager(config=None, **kwargs):
    return SensorManager(config, source='physical_uno', **kwargs)
