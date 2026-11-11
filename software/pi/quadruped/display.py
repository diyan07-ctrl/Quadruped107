"""Optional Pi-owned display; no display I/O runs on a control or STOP thread."""
from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class DisplayFrame:
    screen: str
    text: str
    eyes: str
    blink: bool


def render(state, tick=0):
    motion=state.get('motion') or {}
    sensors=state.get('sensors') or {}
    vision=state.get('vision') or {}
    link=state.get('sensorLink') or state.get('link') or {}
    screen,text,eyes='idle','ROBOT IDLE','neutral'
    if not state:
        screen,text='startup','STARTING'
    elif motion.get('stopping') or motion.get('appMode')=='stop':
        screen,text,eyes='stop','STOP','closed'
    elif link.get('connected') is False or sensors.get('fault'):
        screen,text,eyes='fault','FAULT / LINK','closed'
    elif any(v.get('pressed') for v in sensors.get('touches',{}).values()):
        screen,text,eyes='touch','TOUCH','happy'
    elif state.get('obstacleVirtual') or (sensors.get('front_m') is not None and sensors['front_m']<=.6):
        screen,text,eyes='obstacle','OBSTACLE','wide'
    elif vision.get('targetFresh'):
        screen,text,eyes='target','TARGET FOUND','curious'
    elif vision.get('behavior')=='SEARCH':
        screen,text,eyes='search','SEARCHING','curious'
    elif sensors.get('observations',{}).get('urm37',{}).get('valid'):
        distance=sensors['observations']['urm37']['measurement']
        screen,text='distance',f'{distance:.2f} M'
    elif motion.get('currentMotion') in {'greeting','tail_wag'}:
        screen,text,eyes='happy','HELLO','happy'
    return DisplayFrame(screen,text,eyes,tick%20==19)


class MockDisplay:
    def __init__(self): self.frames=[]
    def connect(self): pass
    def show(self,frame):
        self.frames.append(frame)
        self.frames=self.frames[-32:]
    def close(self): pass


class SSD1306:
    """Explicit reference backend. Requires confirmed SSD1306 and 3.3 V I2C compatibility.

    Optional smbus2 and Pillow imports happen only in this worker. Bounded 16-byte
    writes use Linux i2c-dev; no automatic address scan or alternate-controller guess.
    """
    def __init__(self,bus=1,address=0x3c):
        if address not in (0x3c,0x3d): raise ValueError('Unreviewed OLED address')
        if type(bus) is not int or not 0<=bus<=10: raise ValueError('Invalid I2C bus')
        self.bus_number,self.address=bus,address
        self.bus=None
    def connect(self):
        from smbus2 import SMBus
        self.bus=SMBus(self.bus_number)
        for command in (0xae,0xd5,0x80,0xa8,0x3f,0xd3,0,0x40,0x8d,0x14,
                        0x20,0,0xa1,0xc8,0xda,0x12,0x81,0x7f,0xd9,0xf1,
                        0xdb,0x40,0xa4,0xa6,0xaf):
            self.bus.write_byte_data(self.address,0,command)
    def show(self,frame):
        from PIL import Image, ImageDraw
        image=Image.new('1',(128,64))
        draw=ImageDraw.Draw(image)
        draw.text((1,0),frame.text[:20],fill=1)
        for x in (26,78):
            closed=frame.blink or frame.eyes=='closed'
            height=2 if closed else 10 if frame.eyes=='happy' else 22
            draw.rounded_rectangle((x,27,x+23,27+height),radius=2,fill=1)
        for command in (0x21,0,127,0x22,0,7): self.bus.write_byte_data(self.address,0,command)
        pixels=image.load()
        data=[sum(int(bool(pixels[x,page*8+bit]))<<bit for bit in range(8))
              for page in range(8) for x in range(128)]
        for start in range(0,1024,16):
            self.bus.write_i2c_block_data(self.address,0x40,data[start:start+16])
    def close(self):
        if self.bus:
            self.bus.close()
            self.bus=None


def make_display_backend(kind,bus=1,address=0x3c):
    if kind=='off': return None
    if kind=='mock': return MockDisplay()
    if kind=='ssd1306': return SSD1306(bus,address)
    raise ValueError('Unknown OLED backend')


class DisplayService:
    def __init__(self,backend,state,*,clock=time.monotonic):
        self.backend,self.state,self.clock=backend,state,clock
        self.lock=threading.Lock()
        self.status=dict(enabled=backend is not None,connected=False,screen='startup',error=None,frames=0)
        self.stop=threading.Event()
        self.worker=threading.Thread(target=self._run,name='oled',daemon=True)
        self.next_update=0.
        self.next_retry=0.
        self.connected=False
    def snapshot(self):
        with self.lock: return dict(self.status)
    def start(self):
        if self.backend: self.worker.start()
    def step(self):
        now=self.clock()
        if not self.backend or now<self.next_update or now<self.next_retry: return
        self.next_update=now+.2
        try:
            if not self.connected:
                self.backend.connect()
                self.connected=True
            frame=render(self.state(),self.status['frames'])
            self.backend.show(frame)
            with self.lock:
                self.status.update(connected=True,screen=frame.screen,error=None,frames=self.status['frames']+1)
        except Exception as error:
            self.connected=False
            self.next_retry=now+2.
            with self.lock: self.status.update(connected=False,error=str(error)[:120])
            try: self.backend.close()
            except Exception: pass
    def _run(self):
        while not self.stop.wait(.05): self.step()
        try: self.backend.close()
        except Exception: pass
    def close(self):
        self.stop.set()
        if self.worker.is_alive(): self.worker.join(.3)
