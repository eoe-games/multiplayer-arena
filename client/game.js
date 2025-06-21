// Advanced Game Client
class GameClient {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();

        // Game state
        this.gameState = 'menu'; // menu, connecting, playing
        this.connected = false;
        this.localPlayerId = null;
        this.playerName = '';

        // Entities
        this.players = new Map();
        this.projectiles = new Map();
        this.particles = [];
        this.explosions = [];

        // Camera
        this.camera = {
            x: 0,
            y: 0,
            targetX: 0,
            targetY: 0,
            shake: 0,
            zoom: 1
        };

        // Input
        this.input = {
            keys: {},
            mouseX: 0,
            mouseY: 0,
            mouseDown: false
        };

        // Performance
        this.fps = 0;
        this.ping = 0;
        this.lastTime = performance.now();
        this.accumulator = 0;
        this.frameTime = 1000 / 60; // 60 FPS

        // Network
        this.lastPositionUpdate = 0;
        this.serverUpdateRate = 1000 / 30; // 30Hz
        this.lastServerUpdate = 0;

        // UI Elements
        this.ui = {
            mainMenu: document.getElementById('mainMenu'),
            gameUI: document.getElementById('gameUI'),
            playerNameInput: document.getElementById('playerName'),
            playBtn: document.getElementById('playBtn'),
            serverStatus: document.getElementById('serverStatus'),
            playerNameDisplay: document.getElementById('playerNameDisplay'),
            kills: document.getElementById('kills'),
            deaths: document.getElementById('deaths'),
            gameTime: document.getElementById('gameTime'),
            ping: document.getElementById('ping'),
            fps: document.getElementById('fps'),
            healthBar: document.getElementById('healthBar'),
            healthText: document.getElementById('healthText'),
            killFeed: document.getElementById('killFeed'),
            leaderboard: document.getElementById('leaderboardContent'),
            chatMessages: document.getElementById('chatMessages'),
            chatInput: document.getElementById('chatInput')
        };

        // Game stats
        this.stats = {
            kills: 0,
            deaths: 0,
            startTime: Date.now()
        };

        // Initialize
        this.setupEventListeners();
        this.checkServerStatus();
        this.startGameLoop();
    }

    setupEventListeners() {
        // Window resize
        window.addEventListener('resize', () => this.resizeCanvas());

        // Menu
        this.ui.playBtn.addEventListener('click', () => this.startGame());
        this.ui.playerNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.startGame();
        });

        // Keyboard
        window.addEventListener('keydown', (e) => {
            this.input.keys[e.key.toLowerCase()] = true;

            // Open chat
            if (e.key === 'Enter' && this.gameState === 'playing') {
                e.preventDefault();
                this.ui.chatInput.focus();
            }
        });

        window.addEventListener('keyup', (e) => {
            this.input.keys[e.key.toLowerCase()] = false;
        });

        // Mouse
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.input.mouseX = e.clientX - rect.left;
            this.input.mouseY = e.clientY - rect.top;
        });

        this.canvas.addEventListener('mousedown', () => {
            this.input.mouseDown = true;
        });

        this.canvas.addEventListener('mouseup', () => {
            this.input.mouseDown = false;
        });

        // Chat
        this.ui.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
                this.ui.chatInput.blur();
            }
        });

        this.ui.chatInput.addEventListener('blur', () => {
            this.ui.chatInput.value = '';
        });
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    checkServerStatus() {
        // Simulate server check
        setTimeout(() => {
            this.ui.serverStatus.classList.add('online');
        }, 1000);
    }

    startGame() {
        this.playerName = this.ui.playerNameInput.value.trim() || 'Player';
        this.ui.playerNameDisplay.textContent = this.playerName;

        // Transition to game
        this.ui.mainMenu.style.display = 'none';
        this.ui.gameUI.style.display = 'block';
        this.gameState = 'connecting';

        // Simulate connection
        setTimeout(() => {
            this.connect();
        }, 500);
    }

    connect() {
        console.log('🔗 Connecting to server...');
        
        // Render URL'ini otomatik algıla
        let serverURL;
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            serverURL = 'ws://localhost:8080/ws';
        } else {
            // Render'da HTTPS kullanıldığı için WSS kullan
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            serverURL = `${protocol}//${window.location.host}/ws`;
        }
        
        console.log('🔗 Connecting to:', serverURL);

        try {
            this.ws = new WebSocket(serverURL);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connected!');
                this.connected = true;
                this.gameState = 'playing';
                this.localPlayerId = Math.floor(Math.random() * 10000);

                this.sendToServer({
                    type: 'PLAYER_JOIN',
                    playerId: this.localPlayerId,
                    name: this.playerName
                });

                const player = {
                    id: this.localPlayerId,
                    name: this.playerName,
                    x: Math.random() * 1600 + 100,
                    y: Math.random() * 800 + 100,
                    vx: 0,
                    vy: 0,
                    rotation: 0,
                    health: 100,
                    maxHealth: 100,
                    radius: 20,
                    color: this.getRandomColor(),
                    score: 0
                };

                this.players.set(this.localPlayerId, player);
                this.addChatMessage('System', 'Connected to server!', '#00ff88');
                
                // Heartbeat başlat - her 5 saniyede bir "canlıyım" mesajı gönder
                this.heartbeatInterval = setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.sendToServer({
                            type: 'HEARTBEAT',
                            playerId: this.localPlayerId
                        });
                    }
                }, 5000);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleServerMessage(data);
                } catch (e) {
                    console.error('Failed to parse server message:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.addChatMessage('System', 'Connection error! Switching to offline mode...', '#ff0000');
                if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
                setTimeout(() => {
                    this.startSimulationMode();
                }, 1000);
            };

            this.ws.onclose = (event) => {
                console.log('📴 WebSocket disconnected:', event.code, event.reason);
                this.connected = false;
                this.addChatMessage('System', 'Disconnected from server! Switching to offline mode...', '#ff0000');
                if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
                setTimeout(() => {
                    this.startSimulationMode();
                }, 1000);
            };

        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.addChatMessage('System', 'Cannot connect to server! Running in offline mode...', '#ffaa00');
            this.startSimulationMode();
        }
    }

    startSimulationMode() {
        console.log('🎮 Starting in simulation mode...');
        this.connected = true;
        this.gameState = 'playing';
        this.localPlayerId = Math.floor(Math.random() * 10000);

        // Create local player
        const player = {
            id: this.localPlayerId,
            name: this.playerName,
            x: Math.random() * 1600 + 100,
            y: Math.random() * 800 + 100,
            vx: 0,
            vy: 0,
            rotation: 0,
            health: 100,
            maxHealth: 100,
            radius: 20,
            color: this.getRandomColor(),
            score: 0
        };

        this.players.set(this.localPlayerId, player);

        // Simulate other players
        for (let i = 0; i < 3; i++) {
            this.spawnBot();
        }

        this.addChatMessage('System', 'Running in offline mode', '#ffaa00');
    }

    sendToServer(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    handleServerMessage(data) {
        switch (data.type) {
            case 'WORLD_STATE':
                this.updateWorldState(data);
                break;

            case 'PLAYER_JOIN':
                this.handlePlayerJoin(data);
                break;

            case 'PLAYER_LEAVE':
                this.handlePlayerLeave(data);
                break;

            case 'PLAYER_UPDATE':
                this.handlePlayerUpdate(data);
                break;

            case 'PLAYER_SHOOT':
                this.handlePlayerShoot(data);
                break;

            case 'PLAYER_HIT':
                this.handlePlayerHit(data);
                break;

            case 'PLAYER_DEATH':
                this.handlePlayerDeath(data);
                break;

            case 'PLAYER_RESPAWN':
                this.handlePlayerRespawn(data);
                break;

            case 'SYNC':
                this.handleSync(data);
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateWorldState(data) {
        if (data.players) {
            data.players.forEach(playerData => {
                let player = this.players.get(playerData.id);
                if (!player) {
                    player = {
                        id: playerData.id,
                        name: playerData.name,
                        radius: 20,
                        color: this.getRandomColor(),
                        maxHealth: 100,
                        x: playerData.x,
                        y: playerData.y,
                        targetX: playerData.x,
                        targetY: playerData.y
                    };
                    this.players.set(playerData.id, player);
                }

                // Smooth update için target pozisyonları güncelle
                player.targetX = playerData.x;
                player.targetY = playerData.y;
                player.vx = playerData.vx || 0;
                player.vy = playerData.vy || 0;
                player.rotation = playerData.rotation || 0;
                player.health = playerData.health || 100;
                player.score = playerData.score || 0;
                player.isDead = playerData.isDead || false;

                player.color = player.color || this.getRandomColor();
                player.maxHealth = player.maxHealth || 100;
                player.isBot = playerData.isBot || (player.id < 0);
            });
        }
    }

    handlePlayerJoin(data) {
        if (data.playerId !== this.localPlayerId) {
            const player = {
                id: data.playerId,
                name: data.name,
                x: data.x || Math.random() * 1600 + 100,
                y: data.y || Math.random() * 800 + 100,
                vx: 0,
                vy: 0,
                rotation: 0,
                health: 100,
                maxHealth: 100,
                radius: 20,
                color: this.getRandomColor(),
                score: 0
            };

            this.players.set(data.playerId, player);
            this.addChatMessage('System', `${data.name} joined the game`, '#00ff88');
        }
    }

    handlePlayerLeave(data) {
        const player = this.players.get(data.playerId);
        if (player) {
            this.players.delete(data.playerId);
            this.addChatMessage('System', `${player.name} left the game`, '#ff8888');
        }
    }

    handlePlayerUpdate(data) {
        const player = this.players.get(data.playerId);
        if (player && data.playerId !== this.localPlayerId) {
            // Smooth interpolation için hedef pozisyonları sakla
            player.targetX = data.x;
            player.targetY = data.y;
            player.vx = data.vx || 0;
            player.vy = data.vy || 0;
            player.rotation = data.rotation || 0;
            
            // Eğer ilk güncelleme ise direkt pozisyona atla
            if (!player.hasOwnProperty('targetX')) {
                player.x = data.x;
                player.y = data.y;
            }
        }
    }

    handlePlayerShoot(data) {
        // Başka bir oyuncu ateş ettiğinde
        if (data.shooterId !== this.localPlayerId) {
            const shooter = this.players.get(data.shooterId);
            if (shooter) {
                // Mermi oluştur
                const projectileId = `${data.shooterId}_${data.timestamp}`;
                const projectile = {
                    id: projectileId,
                    shooterId: data.shooterId,
                    x: data.x,
                    y: data.y,
                    vx: Math.cos(data.rotation) * 800,
                    vy: Math.sin(data.rotation) * 800,
                    radius: 5,
                    damage: 20,
                    lifetime: 2
                };
                
                this.projectiles.set(projectileId, projectile);
                
                // Efektler
                this.createMuzzleFlash(data.x, data.y, data.rotation);
                this.playSound('shoot');
            }
        }
    }

    handlePlayerHit(data) {
        const victim = this.players.get(data.victimId);
        if (victim) {
            victim.health = data.health;
            
            // Hit efekti oluştur
            this.createHitEffect(victim.x, victim.y);
            
            // Kendi karakterimize vurulduysa ekranı salla
            if (data.victimId === this.localPlayerId) {
                this.camera.shake = 10;
            }
        }
    }

    handlePlayerDeath(data) {
        const victim = this.players.get(data.victimId);
        const killer = this.players.get(data.shooterId);
        
        if (victim) {
            victim.health = 0;
            victim.isDead = true;  // 🔥 Ölü olarak işaretle
            this.createExplosion(victim.x, victim.y);
        }
        
        // Kill feed'e ekle
        this.addKillFeedEntry(data.killerName, data.victimName);
        
        // Skor güncelle
        if (killer) {
            killer.score = (killer.score || 0) + 1;
        }
        
        if (data.shooterId === this.localPlayerId) {
            this.stats.kills++;
        }
        if (data.victimId === this.localPlayerId) {
            this.stats.deaths++;
        }
    }

    handlePlayerRespawn(data) {
        const player = this.players.get(data.playerId);
        if (player) {
            player.x = data.x;
            player.y = data.y;
            player.health = data.health;
            player.isDead = false;  // 🔥 Artık ölü değil
            
            // Respawn efekti
            for (let i = 0; i < 10; i++) {
                const angle = (Math.PI * 2 * i) / 10;
                this.particles.push({
                    x: data.x + Math.cos(angle) * 20,
                    y: data.y + Math.sin(angle) * 20,
                    vx: Math.cos(angle) * 100,
                    vy: Math.sin(angle) * 100,
                    life: 0.5,
                    maxLife: 0.5,
                    color: '#00ff88',
                    size: 3
                });
            }
        }
    }

    handleSync(data) {
        // Server ile senkronizasyon - daha doğru ping hesaplama
        const now = Date.now();
        const serverTime = data.serverTime * 1000; // Server timestamp'i millisaniye'ye çevir
        
        // Tek yönlü gecikme tahmini (daha doğru)
        this.ping = Math.max(0, Math.round(now - serverTime));
        
        // Çok yüksek ping değerlerini sınırla
        if (this.ping > 999) {
            this.ping = 999;
        }
    }

    update(deltaTime) {
        if (this.gameState !== 'playing') return;

        // Update local player
        this.updateLocalPlayer(deltaTime);

        // Update camera
        this.updateCamera(deltaTime);

        // Update other entities
        this.updateOtherPlayers(deltaTime);  // Yeni fonksiyon
        this.updateBots(deltaTime);
        this.updateProjectiles(deltaTime);
        this.updateParticles(deltaTime);
        this.updateExplosions(deltaTime);

        // Update UI
        this.updateUI();
    }

    updateOtherPlayers(deltaTime) {
        // Diğer oyuncuları smooth interpolate et
        this.players.forEach(player => {
            if (player.id === this.localPlayerId || player.isBot) return;
            
            // Hedef pozisyona doğru interpolate et
            if (player.targetX !== undefined && player.targetY !== undefined) {
                const dx = player.targetX - player.x;
                const dy = player.targetY - player.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance > 1) {
                    // Smooth interpolation
                    const lerpFactor = 0.2; // Ne kadar hızlı interpolate edileceği
                    player.x += dx * lerpFactor;
                    player.y += dy * lerpFactor;
                }
            }
        });
    }

    updateLocalPlayer(deltaTime) {
        const player = this.players.get(this.localPlayerId);
        if (!player) return;

        // Movement
        const speed = 300;
        let dx = 0, dy = 0;

        if (this.input.keys['w']) dy -= 1;
        if (this.input.keys['s']) dy += 1;
        if (this.input.keys['a']) dx -= 1;
        if (this.input.keys['d']) dx += 1;

        // Normalize diagonal movement
        if (dx !== 0 && dy !== 0) {
            dx *= 0.707;
            dy *= 0.707;
        }

        // Apply movement
        player.vx = dx * speed;
        player.vy = dy * speed;

        // Update position
        const oldX = player.x;
        const oldY = player.y;
        
        player.x += player.vx * deltaTime;
        player.y += player.vy * deltaTime;

        // World bounds
        player.x = Math.max(50, Math.min(2000 - 50, player.x));
        player.y = Math.max(50, Math.min(1200 - 50, player.y));

        // Update rotation to face mouse
        const worldMouseX = this.input.mouseX + this.camera.x;
        const worldMouseY = this.input.mouseY + this.camera.y;
        player.rotation = Math.atan2(worldMouseY - player.y, worldMouseX - player.x);

        // Pozisyon değişikliğinde server'a gönder (rate limited)
        if (!this.lastPositionUpdate) this.lastPositionUpdate = 0;
        const now = Date.now();
        
        // Her 50ms'de bir veya önemli değişikliklerde gönder
        const positionChanged = Math.abs(oldX - player.x) > 1 || Math.abs(oldY - player.y) > 1;
        const rotationChanged = Math.abs((player.lastSentRotation || 0) - player.rotation) > 0.1;
        
        if (positionChanged || rotationChanged) {
            if (now - this.lastPositionUpdate > 50) {  // 20 updates per second max
                this.sendToServer({
                    type: 'PLAYER_UPDATE',
                    playerId: this.localPlayerId,
                    x: player.x,
                    y: player.y,
                    vx: player.vx,
                    vy: player.vy,
                    rotation: player.rotation
                });
                this.lastPositionUpdate = now;
                player.lastSentRotation = player.rotation;
            }
        }

        // Shooting
        if (this.input.mouseDown) {
            this.shoot(player);
        }
    }

    updateBots(deltaTime) {
        // Client tarafında botları interpolate et
        this.players.forEach(bot => {
            if (!bot.isBot || bot.isDead) return;

            // Hedef pozisyona doğru smooth hareket
            if (bot.targetX !== undefined && bot.targetY !== undefined) {
                const dx = bot.targetX - bot.x;
                const dy = bot.targetY - bot.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance > 1) {
                    // Velocity bazlı interpolation
                    if (bot.vx !== 0 || bot.vy !== 0) {
                        bot.x += bot.vx * deltaTime;
                        bot.y += bot.vy * deltaTime;
                    } else {
                        // Fallback to lerp
                        const lerpFactor = 0.15;
                        bot.x += dx * lerpFactor;
                        bot.y += dy * lerpFactor;
                    }
                }
            }

            // Bounds
            bot.x = Math.max(50, Math.min(2000 - 50, bot.x));
            bot.y = Math.max(50, Math.min(1200 - 50, bot.y));
        });
    }

    shoot(shooter) {
        // Rate limiting
        if (!shooter.lastShot) shooter.lastShot = 0;
        const now = Date.now();
        if (now - shooter.lastShot < 200) return; // 5 shots per second
        shooter.lastShot = now;

        // Create projectile
        const projectileId = `${shooter.id}_${now}`;
        const projectile = {
            id: projectileId,
            shooterId: shooter.id,
            x: shooter.x + Math.cos(shooter.rotation) * 30,
            y: shooter.y + Math.sin(shooter.rotation) * 30,
            vx: Math.cos(shooter.rotation) * 800,
            vy: Math.sin(shooter.rotation) * 800,
            radius: 5,
            damage: 20,
            lifetime: 2
        };

        this.projectiles.set(projectileId, projectile);

        // Server'a ateş bilgisini gönder
        if (shooter.id === this.localPlayerId) {
            this.sendToServer({
                type: 'PLAYER_SHOOT',
                playerId: shooter.id,
                x: projectile.x,
                y: projectile.y,
                rotation: shooter.rotation
            });
        }

        // Muzzle flash effect
        this.createMuzzleFlash(projectile.x, projectile.y, shooter.rotation);

        // Camera shake for local player
        if (shooter.id === this.localPlayerId) {
            this.camera.shake = 5;
        }

        // Sound effect (placeholder)
        this.playSound('shoot');
    }

    updateProjectiles(deltaTime) {
        this.projectiles.forEach((projectile, id) => {
            // Update position
            projectile.x += projectile.vx * deltaTime;
            projectile.y += projectile.vy * deltaTime;
            projectile.lifetime -= deltaTime;

            // Check collisions with players
            this.players.forEach(player => {
                if (player.id === projectile.shooterId) return;
                if (player.isDead) return;  // 🔥 Ölü oyunculara mermi geçmez

                const dist = Math.hypot(player.x - projectile.x, player.y - projectile.y);
                if (dist < player.radius + projectile.radius) {
                    // Hit!
                    this.handleHit(player, projectile);
                    this.projectiles.delete(id);
                    return;
                }
            });

            // Remove if out of bounds or expired
            if (projectile.lifetime <= 0 ||
                projectile.x < 0 || projectile.x > 2000 ||
                projectile.y < 0 || projectile.y > 1200) {
                this.projectiles.delete(id);
            }
        });
    }

    handleHit(player, projectile) {
        // 🔥 Ölü oyuncuya vurulamaz
        if (player.isDead) return;
        
        // Hit efekti
        this.createHitEffect(player.x, player.y);
        
        // Server'a hit bilgisi gönder
        if (projectile.shooterId === this.localPlayerId) {
            this.sendToServer({
                type: 'PLAYER_HIT',
                shooterId: projectile.shooterId,
                victimId: player.id,
                damage: projectile.damage
            });
        }
        
        // Mermiyi sil
        this.projectiles.delete(projectile.id);
    }

    handleKill(victim, killerId) {
        const killer = this.players.get(killerId);

        // Update scores
        if (killer) {
            killer.score++;
            if (killerId === this.localPlayerId) {
                this.stats.kills++;
            }
        }

        if (victim.id === this.localPlayerId) {
            this.stats.deaths++;
        }

        // Create explosion
        this.createExplosion(victim.x, victim.y);

        // Add kill feed entry
        this.addKillFeedEntry(killer?.name || 'Unknown', victim.name);

        // Respawn
        setTimeout(() => {
            victim.health = victim.maxHealth;
            victim.x = Math.random() * 1600 + 100;
            victim.y = Math.random() * 800 + 100;
        }, 3000);
    }

    createMuzzleFlash(x, y, angle) {
        for (let i = 0; i < 5; i++) {
            const spread = (Math.random() - 0.5) * 0.3;
            const velocity = 300 + Math.random() * 200;

            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle + spread) * velocity,
                vy: Math.sin(angle + spread) * velocity,
                life: 0.2,
                maxLife: 0.2,
                color: '#ffff00',
                size: 3
            });
        }
    }

    createHitEffect(x, y) {
        for (let i = 0; i < 10; i++) {
            const angle = Math.random() * Math.PI * 2;
            const velocity = 100 + Math.random() * 200;

            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * velocity,
                vy: Math.sin(angle) * velocity,
                life: 0.5,
                maxLife: 0.5,
                color: '#ff0000',
                size: 2
            });
        }
    }

    createExplosion(x, y) {
        this.explosions.push({
            x: x,
            y: y,
            radius: 0,
            maxRadius: 80,
            life: 0.5,
            maxLife: 0.5
        });

        // Particles
        for (let i = 0; i < 20; i++) {
            const angle = (Math.PI * 2 * i) / 20;
            const velocity = 200 + Math.random() * 300;

            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * velocity,
                vy: Math.sin(angle) * velocity,
                life: 1,
                maxLife: 1,
                color: Math.random() > 0.5 ? '#ff6600' : '#ffaa00',
                size: 4
            });
        }
    }

    updateParticles(deltaTime) {
        this.particles = this.particles.filter(particle => {
            particle.x += particle.vx * deltaTime;
            particle.y += particle.vy * deltaTime;
            particle.vy += 200 * deltaTime; // Gravity
            particle.life -= deltaTime;

            return particle.life > 0;
        });
    }

    updateExplosions(deltaTime) {
        this.explosions = this.explosions.filter(explosion => {
            explosion.radius += 300 * deltaTime;
            if (explosion.radius > explosion.maxRadius) {
                explosion.radius = explosion.maxRadius;
            }
            explosion.life -= deltaTime;

            return explosion.life > 0;
        });
    }

    updateCamera(deltaTime) {
        const player = this.players.get(this.localPlayerId);
        if (!player) return;

        // Smooth camera follow
        this.camera.targetX = player.x - this.canvas.width / 2;
        this.camera.targetY = player.y - this.canvas.height / 2;

        const smoothing = 0.1;
        this.camera.x += (this.camera.targetX - this.camera.x) * smoothing;
        this.camera.y += (this.camera.targetY - this.camera.y) * smoothing;

        // Camera shake
        if (this.camera.shake > 0) {
            this.camera.x += (Math.random() - 0.5) * this.camera.shake;
            this.camera.y += (Math.random() - 0.5) * this.camera.shake;
            this.camera.shake *= 0.9;
        }

        // Bounds
        this.camera.x = Math.max(0, Math.min(2000 - this.canvas.width, this.camera.x));
        this.camera.y = Math.max(0, Math.min(1200 - this.canvas.height, this.camera.y));
    }

    render() {
        // Clear
        this.ctx.fillStyle = '#0a0a0a';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Save context
        this.ctx.save();

        // Apply camera transform
        this.ctx.translate(-this.camera.x, -this.camera.y);

        // Draw game world
        this.drawGrid();
        this.drawWorldBounds();

        // Draw entities (sorted by layer)
        this.drawExplosions();
        this.drawProjectiles();
        this.drawPlayers();
        this.drawParticles();

        // Restore context
        this.ctx.restore();

        // Draw UI overlay
        this.drawRadar();
        this.drawCrosshair();
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        this.ctx.lineWidth = 1;

        const gridSize = 100;

        for (let x = 0; x <= 2000; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, 1200);
            this.ctx.stroke();
        }

        for (let y = 0; y <= 1200; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(2000, y);
            this.ctx.stroke();
        }
    }

    drawWorldBounds() {
        this.ctx.strokeStyle = '#ff0000';
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(0, 0, 2000, 1200);
    }

    drawPlayers() {
        this.players.forEach(player => {
            // 🔥 Ölü oyuncuları yarı saydam çiz
            if (player.isDead) {
                this.ctx.globalAlpha = 0.3;
            }
            
            this.ctx.save();
            this.ctx.translate(player.x, player.y);

            // Shadow
            this.ctx.fillStyle = 'rgba(0,0,0,0.3)';
            this.ctx.beginPath();
            this.ctx.ellipse(0, 5, player.radius, player.radius * 0.5, 0, 0, Math.PI * 2);
            this.ctx.fill();

            // Player body
            this.ctx.rotate(player.rotation);

            // Gradient fill
            const gradient = this.ctx.createRadialGradient(0, 0, 0, 0, 0, player.radius);
            gradient.addColorStop(0, this.lightenColor(player.color, 30));
            gradient.addColorStop(1, player.color);

            this.ctx.fillStyle = gradient;
            this.ctx.beginPath();
            this.ctx.arc(0, 0, player.radius, 0, Math.PI * 2);
            this.ctx.fill();

            // Direction indicator
            this.ctx.fillStyle = 'white';
            this.ctx.fillRect(player.radius - 5, -3, 15, 6);

            this.ctx.restore();

            // Health bar
            if (player.health < player.maxHealth && !player.isDead) {
                this.drawHealthBar(player);
            }

            // Name
            this.ctx.fillStyle = player.isDead ? 'rgba(255,255,255,0.5)' : 'white';
            this.ctx.font = 'bold 14px Orbitron';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(player.name, player.x, player.y - 35);
            
            // 🔥 Alpha'yı resetle
            this.ctx.globalAlpha = 1;
        });
    }

    drawHealthBar(player) {
        const barWidth = 40;
        const barHeight = 4;
        const x = player.x - barWidth / 2;
        const y = player.y - 25;

        // Background
        this.ctx.fillStyle = 'rgba(0,0,0,0.5)';
        this.ctx.fillRect(x, y, barWidth, barHeight);

        // Health
        const healthPercent = player.health / player.maxHealth;
        const healthColor = healthPercent > 0.5 ? '#00ff00' :
            healthPercent > 0.25 ? '#ffaa00' : '#ff0000';

        this.ctx.fillStyle = healthColor;
        this.ctx.fillRect(x, y, barWidth * healthPercent, barHeight);
    }

    drawProjectiles() {
        this.ctx.shadowBlur = 10;
        this.ctx.shadowColor = '#ffff00';

        this.projectiles.forEach(projectile => {
            this.ctx.fillStyle = '#ffff00';
            this.ctx.beginPath();
            this.ctx.arc(projectile.x, projectile.y, projectile.radius, 0, Math.PI * 2);
            this.ctx.fill();

            // Trail
            this.ctx.strokeStyle = 'rgba(255,255,0,0.5)';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(projectile.x, projectile.y);
            this.ctx.lineTo(
                projectile.x - projectile.vx * 0.05,
                projectile.y - projectile.vy * 0.05
            );
            this.ctx.stroke();
        });

        this.ctx.shadowBlur = 0;
    }

    drawParticles() {
        this.particles.forEach(particle => {
            const alpha = particle.life / particle.maxLife;
            this.ctx.fillStyle = particle.color + Math.floor(alpha * 255).toString(16).padStart(2, '0');
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, particle.size * alpha, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    drawExplosions() {
        this.explosions.forEach(explosion => {
            const alpha = explosion.life / explosion.maxLife;

            // Shockwave
            this.ctx.strokeStyle = `rgba(255,255,255,${alpha * 0.5})`;
            this.ctx.lineWidth = 3;
            this.ctx.beginPath();
            this.ctx.arc(explosion.x, explosion.y, explosion.radius, 0, Math.PI * 2);
            this.ctx.stroke();

            // Inner glow
            const gradient = this.ctx.createRadialGradient(
                explosion.x, explosion.y, 0,
                explosion.x, explosion.y, explosion.radius
            );
            gradient.addColorStop(0, `rgba(255,200,50,${alpha * 0.3})`);
            gradient.addColorStop(1, 'rgba(255,100,0,0)');

            this.ctx.fillStyle = gradient;
            this.ctx.beginPath();
            this.ctx.arc(explosion.x, explosion.y, explosion.radius, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    drawRadar() {
        const radarSize = 150;
        const radarX = this.canvas.width - radarSize - 20;
        const radarY = this.canvas.height - radarSize - 20;
        const scale = radarSize / 2000;

        // Background
        this.ctx.fillStyle = 'rgba(0,0,0,0.7)';
        this.ctx.strokeStyle = 'rgba(0,255,0,0.5)';
        this.ctx.lineWidth = 2;

        this.ctx.beginPath();
        this.ctx.arc(radarX + radarSize/2, radarY + radarSize/2, radarSize/2, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.stroke();

        // Grid
        this.ctx.strokeStyle = 'rgba(0,255,0,0.2)';
        this.ctx.lineWidth = 1;

        this.ctx.beginPath();
        this.ctx.moveTo(radarX, radarY + radarSize/2);
        this.ctx.lineTo(radarX + radarSize, radarY + radarSize/2);
        this.ctx.moveTo(radarX + radarSize/2, radarY);
        this.ctx.lineTo(radarX + radarSize/2, radarY + radarSize);
        this.ctx.stroke();

        // Players
        this.players.forEach(player => {
            const x = radarX + player.x * scale;
            const y = radarY + player.y * scale;

            this.ctx.fillStyle = player.id === this.localPlayerId ? '#00ff00' : '#ff0000';
            this.ctx.beginPath();
            this.ctx.arc(x, y, 3, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }

    drawCrosshair() {
        this.ctx.strokeStyle = 'rgba(255,255,255,0.8)';
        this.ctx.lineWidth = 2;

        const size = 20;
        const gap = 5;

        // Horizontal lines
        this.ctx.beginPath();
        this.ctx.moveTo(this.input.mouseX - size, this.input.mouseY);
        this.ctx.lineTo(this.input.mouseX - gap, this.input.mouseY);
        this.ctx.moveTo(this.input.mouseX + gap, this.input.mouseY);
        this.ctx.lineTo(this.input.mouseX + size, this.input.mouseY);

        // Vertical lines
        this.ctx.moveTo(this.input.mouseX, this.input.mouseY - size);
        this.ctx.lineTo(this.input.mouseX, this.input.mouseY - gap);
        this.ctx.moveTo(this.input.mouseX, this.input.mouseY + gap);
        this.ctx.lineTo(this.input.mouseX, this.input.mouseY + size);

        this.ctx.stroke();
    }

    updateUI() {
        // FPS
        this.ui.fps.textContent = Math.round(this.fps);

        // Ping - gerçek değeri göster
        this.ui.ping.textContent = this.ping || 'N/A';

        // Stats
        this.ui.kills.textContent = this.stats.kills;
        this.ui.deaths.textContent = this.stats.deaths;

        // Game time
        const elapsed = Date.now() - this.stats.startTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        this.ui.gameTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        // Health
        const player = this.players.get(this.localPlayerId);
        if (player) {
            const healthPercent = (player.health / player.maxHealth) * 100;
            this.ui.healthBar.style.width = `${healthPercent}%`;
            this.ui.healthText.textContent = `${Math.ceil(player.health)}/${player.maxHealth}`;

            // Change color based on health
            if (healthPercent > 50) {
                this.ui.healthBar.style.background = 'linear-gradient(90deg, #00ff00, #00cc00)';
            } else if (healthPercent > 25) {
                this.ui.healthBar.style.background = 'linear-gradient(90deg, #ffaa00, #ff8800)';
            } else {
                this.ui.healthBar.style.background = 'linear-gradient(90deg, #ff3333, #cc0000)';
            }
        }

        // Leaderboard
        this.updateLeaderboard();
    }

    updateLeaderboard() {
        const sortedPlayers = Array.from(this.players.values())
            .sort((a, b) => b.score - a.score)
            .slice(0, 5);

        this.ui.leaderboard.innerHTML = sortedPlayers.map((player, index) => `
            <div class="leaderboard-item">
                <span>${index + 1}. ${player.name}</span>
                <span>${player.score}</span>
            </div>
        `).join('');
    }

    addKillFeedEntry(killer, victim) {
        const entry = document.createElement('div');
        entry.className = 'kill-feed-item';
        entry.innerHTML = `<span style="color: #00ff00">${killer}</span> eliminated <span style="color: #ff3333">${victim}</span>`;

        this.ui.killFeed.appendChild(entry);

        // Remove after 5 seconds
        setTimeout(() => {
            entry.style.opacity = '0';
            setTimeout(() => entry.remove(), 300);
        }, 5000);

        // Keep only last 5 entries
        while (this.ui.killFeed.children.length > 5) {
            this.ui.killFeed.removeChild(this.ui.killFeed.firstChild);
        }
    }

    addChatMessage(sender, message, color = '#ffffff') {
        const entry = document.createElement('div');
        entry.className = 'chat-message';
        entry.innerHTML = `<span style="color: ${color}">${sender}:</span> ${message}`;

        this.ui.chatMessages.appendChild(entry);
        this.ui.chatMessages.scrollTop = this.ui.chatMessages.scrollHeight;

        // Keep only last 20 messages
        while (this.ui.chatMessages.children.length > 20) {
            this.ui.chatMessages.removeChild(this.ui.chatMessages.firstChild);
        }
    }

    sendChatMessage() {
        const message = this.ui.chatInput.value.trim();
        if (!message) return;

        this.addChatMessage(this.playerName, message);
        this.ui.chatInput.value = '';

        // Server'a chat mesajı gönder
        this.sendToServer({
            type: 'CHAT_MESSAGE',
            playerId: this.localPlayerId,
            message: message
        });
    }

    playSound(type) {
        // Placeholder for sound effects
        // In real implementation, use Web Audio API or HTML5 Audio
        console.log(`🔊 Playing sound: ${type}`);
    }

    getRandomColor() {
        const colors = [
            '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57',
            '#ff9ff3', '#54a0ff', '#48dbfb', '#00d2d3', '#ff6348'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    lightenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255))
            .toString(16).slice(1);
    }

    spawnBot() {
        const botId = -Math.floor(Math.random() * 10000);
        const bot = {
            id: botId,
            name: `Bot${Math.abs(botId)}`,
            x: Math.random() * 1600 + 100,
            y: Math.random() * 800 + 100,
            vx: 0,
            vy: 0,
            rotation: 0,
            health: 100,
            maxHealth: 100,
            radius: 20,
            color: this.getRandomColor(),
            score: Math.floor(Math.random() * 10),
            isBot: true
        };

        this.players.set(botId, bot);
    }

    startGameLoop() {
        const gameLoop = (currentTime) => {
            // Calculate delta time
            const deltaTime = (currentTime - this.lastTime) / 1000;
            this.lastTime = currentTime;

            // Update FPS
            this.fps = 1 / deltaTime;

            // Fixed timestep with interpolation
            this.accumulator += deltaTime;

            while (this.accumulator >= this.frameTime / 1000) {
                this.update(this.frameTime / 1000);
                this.accumulator -= this.frameTime / 1000;
            }

            // Render with interpolation
            const interpolation = this.accumulator / (this.frameTime / 1000);
            this.render(interpolation);

            requestAnimationFrame(gameLoop);
        };

        requestAnimationFrame(gameLoop);
    }
}

// Initialize game when DOM is loaded
window.addEventListener('DOMContentLoaded', () => {
    const game = new GameClient();
    console.log('🎮 Advanced Game Client initialized!');

    // Expose game instance for debugging
    window.game = game;
});
