from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
project_id = "12654003615"
parent = f"projects/{project_id}"

print(f"ADC setup! Try to get secrets: {project_id}")
