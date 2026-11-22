import os,runpy,urllib.request
from pathlib import Path
from gsm_wire_client import Capture
directory=Path('vision-wire');directory.mkdir(exist_ok=False)
original=urllib.request.urlopen
def capture(request,*args,**kwargs):
 if isinstance(request,str): request=urllib.request.Request(request)
 return Capture(original(request,*args,**kwargs),request,directory)
urllib.request.urlopen=capture
runpy.run_path('reference/tests/vision_accuracy_check.py',run_name='__main__')
