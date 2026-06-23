import os
print("GOOGLE_API_KEY:", "FOUND" if os.environ.get("GOOGLE_API_KEY") else "NOT FOUND")
