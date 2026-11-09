"""Versioned local preferences, separate from operator-supplied config files."""
import json
import os
from pathlib import Path
import tempfile
from .autonomy import VisionSettings

def load_state(path):
    path=Path(path)
    if path.stat().st_size>4096: raise ValueError("Vision state exceeds 4096 bytes")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.get("schema")!=1 or type(data.get("revision")) is not int or data["revision"]<1:
        raise ValueError("Invalid vision state version/revision")
    return VisionSettings.from_dict(data["settings"]),data["revision"]

def save_state(path,settings,revision):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            os.chmod(temporary,0o600)
            json.dump(dict(schema=1,revision=revision,settings=settings.to_dict()),stream,indent=2,allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
        temporary=None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
