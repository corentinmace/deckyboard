import asyncio
import secrets
import subprocess
from aiohttp import web
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Plugin:
    async def _main(self):
        self.server_runner = None
        self.server_site = None
        self.access_code = None
        self.connected_clients = set()
        logger.info("Deckyboard plugin initialized")
        
    async def _unload(self):
        logger.info("Deckyboard plugin unloading")
        if self.server_site:
            await self.server_site.stop()
        if self.server_runner:
            await self.server_runner.cleanup()
    
    async def start_server(self, port=8765):
        """Starts the WebSocket server"""
        if self.server_runner:
            return {"success": False, "error": "Server already running"}
        
        # Génère un code à 6 caractères
        self.access_code = secrets.token_urlsafe(4)[:6].upper()
        logger.info(f"Starting server with code: {self.access_code}")
        
        app = web.Application()
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/', self.serve_client_page)
        
        self.server_runner = web.AppRunner(app)
        await self.server_runner.setup()
        self.server_site = web.TCPSite(self.server_runner, '0.0.0.0', port)
        
        await self.server_site.start()
        
        logger.info(f"Server started on port {port}")
        
        return {
            "success": True,
            "code": self.access_code,
            "port": port
        }
    
    async def stop_server(self):
        """Stops the server"""
        if self.server_site:
            await self.server_site.stop()
            self.server_site = None
        if self.server_runner:
            await self.server_runner.cleanup()
            self.server_runner = None
        self.access_code = None
        self.connected_clients.clear()
        logger.info("Server stopped")
        return {"success": True}
    
    async def get_server_status(self):
        """Returns server status"""
        return {
            "running": self.server_runner is not None,
            "code": self.access_code,
            "clients": len(self.connected_clients)
        }
    
    async def websocket_handler(self, request):
        """Gère les connexions WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        authenticated = False
        logger.info("New WebSocket connection")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        
                        if not authenticated:
                            if data.get('type') == 'auth':
                                if data.get('code') == self.access_code:
                                    authenticated = True
                                    self.connected_clients.add(ws)
                                    await ws.send_json({"type": "auth_success"})
                                    logger.info("Client authenticated")
                                else:
                                    await ws.send_json({"type": "auth_failed"})
                                    await ws.close()
                                    logger.warning("Client authentication failed")
                                    break
                            continue
                        
                        if data.get('type') == 'keydown':
                            await self.inject_key(data['key'], data.get('modifiers', []), press=True)
                        elif data.get('type') == 'keyup':
                            await self.inject_key(data['key'], data.get('modifiers', []), press=False)
                        
                        await ws.send_json({"type": "ack", "key": data['key']})
                    
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        await ws.send_json({"type": "error", "message": str(e)})
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket connection closed with exception {ws.exception()}')
                    break
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        
        finally:
            if ws in self.connected_clients:
                self.connected_clients.remove(ws)
            logger.info("WebSocket connection closed")
        
        return ws
    
    async def inject_key(self, key, modifiers, press=True):
        """Inject key via ydotool"""
        try:
            key_map = {
                'Enter': '28',
                'Backspace': '14',
                'Tab': '15',
                'Escape': '1',
                'ArrowUp': '103',
                'ArrowDown': '108',
                'ArrowLeft': '105',
                'ArrowRight': '106',
                'Delete': '111',
                'Home': '102',
                'End': '107',
                'PageUp': '104',
                'PageDown': '109',
                'Insert': '110',
                'Space': '57',
            }
            
            if key in key_map:
                keycode = key_map[key]
                action = '1' if press else '0'
                subprocess.run(['ydotool', 'key', f'{keycode}:{action}'], 
                             capture_output=True, check=False)
                logger.info(f"Injected key: {key} ({keycode}:{action})")
            else:
                if press and len(key) == 1:
                    subprocess.run(['ydotool', 'type', key], 
                                 capture_output=True, check=False)
                    logger.info(f"Typed character: {key}")
        
        except Exception as e:
            logger.error(f"Error injecting key: {e}")
            logger.info(f"Error injecting key: {e}")
    
    async def serve_client_page(self, request):
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steam Deck Remote Keyboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }
        #auth-screen, #keyboard-screen { display: none; }
        #auth-screen.active, #keyboard-screen.active { display: block; }
        input, textarea {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            font-size: 16px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            box-sizing: border-box;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            background: #0066cc;
            color: white;
            border: none;
            cursor: pointer;
        }
        button:hover { background: #0052a3; }
        #status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .connected { background: #1a5f1a; }
        .disconnected { background: #5f1a1a; }
        #auth-error {
            color: #ff6b6b;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div id="auth-screen" class="active">
        <h1>Steam Deck Remote Keyboard</h1>
        <input type="text" id="code-input" placeholder="Enter 6-character code" maxlength="6">
        <button onclick="authenticate()">Connect</button>
        <div id="auth-error"></div>
    </div>
    
    <div id="keyboard-screen">
        <h1>Connected to Steam Deck</h1>
        <div id="status" class="connected">Connected</div>
        <textarea id="input" placeholder="Start typing here..." rows="10"></textarea>
        <p>All keystrokes are sent in real-time to your Steam Deck.</p>
    </div>
    
    <script>
        let ws = null;
        let authenticated = false;
        
        function authenticate() {
            const code = document.getElementById('code-input').value.toUpperCase();
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                ws.send(JSON.stringify({ type: 'auth', code: code }));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('Received:', data);
                
                if (data.type === 'auth_success') {
                    authenticated = true;
                    document.getElementById('auth-screen').classList.remove('active');
                    document.getElementById('keyboard-screen').classList.add('active');
                    document.getElementById('input').focus();
                } else if (data.type === 'auth_failed') {
                    document.getElementById('auth-error').textContent = 'Invalid code';
                } else if (data.type === 'error') {
                    console.error('Server error:', data.message);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                document.getElementById('status').textContent = 'Connection error';
                document.getElementById('status').classList.remove('connected');
                document.getElementById('status').classList.add('disconnected');
            };
            
            ws.onclose = () => {
                console.log('WebSocket closed');
                authenticated = false;
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').classList.remove('connected');
                document.getElementById('status').classList.add('disconnected');
            };
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('input');
            
            input.addEventListener('keydown', (e) => {
                if (!authenticated || !ws || ws.readyState !== WebSocket.OPEN) return;
                
                // Empêche le comportement par défaut pour certaines touches
                if (['Tab', 'Escape'].includes(e.key)) {
                    e.preventDefault();
                }
                
                const message = {
                    type: 'keydown',
                    key: e.key,
                    modifiers: [
                        e.ctrlKey ? 'ctrl' : null,
                        e.altKey ? 'alt' : null,
                        e.shiftKey ? 'shift' : null
                    ].filter(Boolean)
                };
                
                console.log('Sending:', message);
                ws.send(JSON.stringify(message));
            });
            
            input.addEventListener('keyup', (e) => {
                if (!authenticated || !ws || ws.readyState !== WebSocket.OPEN) return;
                
                const message = {
                    type: 'keyup',
                    key: e.key
                };
                
                ws.send(JSON.stringify(message));
            });
        });
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')