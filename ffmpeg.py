import subprocess

try:
    result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(result.stdout.decode())
except FileNotFoundError:
    print("ffmpeg not found")