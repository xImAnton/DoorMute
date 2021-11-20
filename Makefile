build:
	docker build -t automute/server .
build-arm:
	docker buildx build --platform linux/arm64/v8 -t automute/server:1.0.2-arm .
build-client:
	pyinstaller --noconfirm --onefile -w --paths "C:/Development/DoorMute/venv/Lib/site-packages" --hidden-import "websockets.legacy" --hidden-import "websockets.legacy.client"  "C:/Development/DoorMute/client.py"
push:
	docker tag automute/server ubuntu:9998/automute
	docker push ubuntu:9998/automute
build-installer:
	pyinstaller --noconfirm --onefile --console --add-data "C:/Development/DoorMute/dist/client.exe;." --add-data "C:/Development/DoorMute/resources;resources/" --paths "C:/Development/DoorMute/venv/Lib/site-packages"  "C:/Development/DoorMute/install.py"
