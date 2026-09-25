import requests
import re
import json

s = requests.Session()
# 1. Post good demo sample
r1 = s.post('http://127.0.0.1:5000/', data={'demo_image': 'good', 'run_mode': 'step'})
print('POST / status:', r1.status_code)

with open("scratch_response.html", "r", encoding="utf-8") as f:
    text = f.read()

# Let's see if the server process running on 5000 is running an OLD version of app.py or template!
print("Has 'current-analysis-id':", "current-analysis-id" in text)
print("Has 'phase2-section':", "phase2-section" in text)
print("Has 'runPhase2':", "runPhase2" in text)
print("Has 'Phase 2':", "Phase 2" in text)
print("Has 'Phase 1':", "Phase 1" in text)

# Print lines around 'Phase 1' or 'Phase 2'
lines = text.splitlines()
for i, l in enumerate(lines):
    if "Phase" in l or "phase" in l or "input" in l or "button" in l:
        print(f"Line {i+1}: {l[:120]}")


