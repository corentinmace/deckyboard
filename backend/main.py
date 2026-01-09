import asyncio
import secrets
import subprocess
from aiohttp import web
import aiohttp

class Plugin:
    async def _main(self):
        self.server_task = None
        self.access_code = None
        self.connected_clients = set()
        
    async def _unload(self):
        if self.server_task:
            self.server_task.cancel()
    
    async def start_server(self, port=8765):
        """Démarre le serveur WebSocket"""
        if self.server_task:
            return {"success": False, "error": "Server already running"}
        
        # Génère un code à 6 caractères
        self.access_code = secrets.token_urlsafe(4)[:6].upper()
        
        app = web.Application()
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/', self.serve_client_page)
        app.router.add_static('/static', './static')
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        
        self.server_task = asyncio.create_task(site.start())
        
        return {
            "success": True,
            "code": self.access_code,
            "port": port
        }
    
    async def stop_server(self):
        """Arrête le serveur"""
        if self.server_task:
            self.server_task.cancel()
            self.server_task = None
            self.access_code = None
            self.connected_clients.clear()
            return {"success": True}
        return {"success": False, "error": "Server not running"}
    
    async def get_server_status(self):
        """Retourne le statut du serveur"""
        return {
            "running": self.server_task is not None,
            "code": self.access_code,
            "clients": len(self.connected_clients)
        }
    
    async def websocket_handler(self, request):
        """Gère les connexions WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        authenticated = False
        
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()
                
                # Authentification
                if not authenticated:
                    if data.get('type') == 'auth':
                        if data.get('code') == self.access_code:
                            authenticated = True
                            self.connected_clients.add(ws)
                            await ws.send_json({"type": "auth_success"})
                        else:
                            await ws.send_json({"type": "auth_failed"})
                            await ws.close()
                            break
                    continue
                
                # Traitement des touches
                if data.get('type') == 'keydown':
                    await self.inject_key(data['key'], data.get('modifiers', []), press=True)
                elif data.get('type') == 'keyup':
                    await self.inject_key(data['key'], data.get('modifiers', []), press=False)
                
                # Acknowledge
                await ws.send_json({"type": "ack"})
            
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
        
        if ws in self.connected_clients:
            self.connected_clients.remove(ws)
        
        return ws
    
    async def inject_key(self, key, modifiers, press=True):
        """Injecte une touche via ydotool"""
        # Mapping JS key → ydotool key code
        key_map = {
            'Enter': '28:1' if press else '28:0',
            'Backspace': '14:1' if press else '14:0',
            'Tab': '15:1' if press else '15:0',
            'Escape': '1:1' if press else '1:0',
            'ArrowUp': '103:1' if press else '103:0',
            'ArrowDown': '108:1' if press else '108:0',
            'ArrowLeft': '105:1' if press else '105:0',
            'ArrowRight': '106:1' if press else '106:0',
            # Pour les lettres/chiffres, on utilise directement type
        }
        
        # Si c'est une touche spéciale
        if key in key_map:
            subprocess.run(['ydotool', 'key', key_map[key]], 
                         capture_output=True)
        else:
            # Pour les caractères normaux, utilise type
            if press:  # On envoie seulement au press, pas au release
                subprocess.run(['ydotool', 'type', key], 
                             capture_output=True)
    
    async def serve_client_page(self, request):
        """Sert la page HTML cliente"""
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
                ws.send(JSON.stringify({ type: 'auth', code: code }));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'auth_success') {
                    authenticated = true;
                    document.getElementById('auth-screen').classList.remove('active');
                    document.getElementById('keyboard-screen').classList.add('active');
                    document.getElementById('input').focus();
                } else if (data.type === 'auth_failed') {
                    document.getElementById('auth-error').textContent = 'Invalid code';
                }
            };
            
            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').classList.remove('connected');
                document.getElementById('status').classList.add('disconnected');
            };
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('input');
            
            input.addEventListener('keydown', (e) => {
                if (!authenticated || !ws) return;
                
                // Empêche le comportement par défaut pour certaines touches
                if (['Tab', 'Escape'].includes(e.key)) {
                    e.preventDefault();
                }
                
                ws.send(JSON.stringify({
                    type: 'keydown',
                    key: e.key,
                    modifiers: [
                        e.ctrlKey ? 'ctrl' : null,
                        e.altKey ? 'alt' : null,
                        e.shiftKey ? 'shift' : null
                    ].filter(Boolean)
                }));
            });
            
            input.addEventListener('keyup', (e) => {
                if (!authenticated || !ws) return;
                
                ws.send(JSON.stringify({
                    type: 'keyup',
                    key: e.key
                }));
            });
        });
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')