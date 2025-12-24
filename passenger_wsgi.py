import sys, os
INTERP = os.path.expanduser("~/domains/idealimage.ru/.venv/python311/bin/python3.11")

if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

from IdealImage_PDJ.wsgi import application