from cmu_graphics import *

#def onAppStart(app):
   # app.sqSize = 200

#def redrawAll(app):
   # cx, cy = app.width/2, app.height/2
    #drawRect(cx, cy, app.sqSize, app.sqSize, fill='purple', align='center')
    #drawLabel('Hello World!', cx, cy, fill='white', 
           #   align='center', bold=True, size=20)

#def main():
 #   runApp()

#main()


#print("setup complete")
"""JUNUBI RUN: Python / CMU Graphics. No external assets needed.
Install: python3 -m pip install cmu-graphics
Run: python3 line_runner.py
Or paste into a CMU Graphics CPCS / 15-112 sandbox.
"""
from cmu_graphics import *
import math
import random

LEFT, RIGHT, TOP, BOTTOM = 150, 750, 275, 635
CENTER = (LEFT + RIGHT) / 2
HORIZONTAL_LINES = (380, 525)
ALL_HORIZONTAL_LINES = (TOP,) + HORIZONTAL_LINES + (BOTTOM,)
START_Y, FINISH_Y = TOP - 30, BOTTOM + 30
MOVE_TOP, MOVE_BOTTOM = TOP - 45, BOTTOM + 40
PLAYER_RADIUS, GUARD_RADIUS = 12, 16
PLAYER_SPEED = 4.4
LEVELS = {1: (1.85, 20), 2: (2.15, 17), 3: (2.5, 14),
          4: (2.8, 11), 5: (3.15, 8)}
BG = rgb(14, 27, 36)
PANEL = rgb(25, 44, 53)
FIELD = rgb(34, 60, 63)
CREAM = rgb(244, 237, 216)
MUTED = rgb(159, 183, 186)
TEAL = rgb(108, 229, 205)
GOLD = rgb(237, 192, 112)
CORAL = rgb(244, 139, 118)
EDGE = rgb(66, 94, 100)
TAUNT = "Haha, you can't catch a Junubi who runs with Cattles"
DASH_DURATION, DASH_COOLDOWN = 10, 180


def clamp(value, low, high):
    return max(low, min(high, value))


def resetRound(app):
    app.roundLevel = app.level
    app.playerX, app.playerY = 295, START_Y
    app.guards = [
        dict(axis='vertical', x=CENTER, y=455, color=GOLD),
        dict(axis='horizontal', x=570, y=TOP, color=CORAL),
        dict(axis='horizontal', x=570, y=HORIZONTAL_LINES[0], color=CORAL),
        dict(axis='horizontal', x=320, y=HORIZONTAL_LINES[1], color=CORAL),
        dict(axis='horizontal', x=570, y=BOTTOM, color=CORAL)]
    for guard in app.guards:
        guard['target'] = app.playerY if guard['axis'] == 'vertical' else app.playerX
        guard['velocity'] = 0
        guard['side'] = -1
    app.keys = set()
    app.roundFrames = 0
    app.delay = 0
    app.messageFrames = 0
    app.cooldown = 0
    app.dashFrames = 0
    app.dashesUsed = 0
    app.passed = set()
    app.trail = []
    app.particles = []
    app.progress = 0


def onAppStart(app):
    app.stepsPerSecond = 60
    app.level = 1
    app.consecutiveTags = 0
    app.wins, app.tags, app.streak = 0, 0, 0
    app.bestTimes = {level: None for level in LEVELS}
    app.bestScores = {level: 0 for level in LEVELS}
    app.lastScore = 0
    app.animationTick = 0
    app.helpReturn = 'ready'
    resetRound(app)
    app.state = 'ready'


def startRound(app):
    resetRound(app)
    app.state = 'countdown'
    app.countdown = 180


def burst(app, x, y, color, count):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)
        app.particles.append(dict(
            x=x, y=y, dx=math.cos(angle) * speed,
            dy=math.sin(angle) * speed - 1,
            life=random.randint(25, 45), color=color))


def updateEffects(app):
    for particle in app.particles:
        particle['x'] += particle['dx']
        particle['y'] += particle['dy']
        particle['dy'] += 0.07
        particle['life'] -= 1
    app.particles = [p for p in app.particles if p['life'] > 0]
    app.trail = [(x, y, life - 1) for x, y, life in app.trail if life > 1]


def touched(px0, py0, px1, py1, gx0, gy0, gx1, gy1):
    # Swept collision prevents a fast dash from skipping a touch.
    x, y = px0 - gx0, py0 - gy0
    dx, dy = (px1 - gx1) - x, (py1 - gy1) - y
    lengthSquared = dx * dx + dy * dy
    t = 0 if lengthSquared == 0 else clamp(
        -(x * dx + y * dy) / lengthSquared, 0, 1)
    return math.hypot(x + t * dx, y + t * dy) <= PLAYER_RADIUS + GUARD_RADIUS


def moveGuards(app, oldX, oldY):
    maxSpeed, reaction = LEVELS[app.roundLevel]
    hit = False
    for index, guard in enumerate(app.guards):
        gx, gy = guard['x'], guard['y']
        vertical = guard['axis'] == 'vertical'
        if (app.roundFrames + index * 3) % reaction == 0:
            guard['target'] = app.playerY if vertical else app.playerX
        coordinate = 'y' if vertical else 'x'
        distance = guard['target'] - guard[coordinate]
        desired = clamp(distance * 0.18, -maxSpeed, maxSpeed)
        guard['velocity'] += clamp(desired - guard['velocity'], -0.24, 0.24)
        low, high = (TOP, BOTTOM) if vertical else (LEFT, RIGHT)
        guard[coordinate] = clamp(guard[coordinate] + guard['velocity'],
                                  low + GUARD_RADIUS, high - GUARD_RADIUS)
        if guard[coordinate] in (low + GUARD_RADIUS, high - GUARD_RADIUS):
            guard['velocity'] = 0
        if touched(oldX, oldY, app.playerX, app.playerY,
                   gx, gy, guard['x'], guard['y']):
            hit = True
    return hit


def checkPasses(app):
    for index, guard in enumerate(app.guards):
        offset = (app.playerX - guard['x'] if guard['axis'] == 'vertical'
                  else app.playerY - guard['y'])
        clearance = PLAYER_RADIUS + GUARD_RADIUS
        side = 1 if offset > clearance else -1 if offset < -clearance else 0
        if side:
            if side != guard['side']:
                app.messageFrames = 150
                app.passed.add(index)
                burst(app, app.playerX, app.playerY, TEAL, 12)
            guard['side'] = side


def advanceGame(app):
    oldX, oldY = app.playerX, app.playerY
    app.roundFrames += 1
    app.messageFrames = max(0, app.messageFrames - 1)
    app.cooldown = max(0, app.cooldown - 1)
    dx = int(bool(app.keys & {'right', 'd'})) - int(bool(app.keys & {'left', 'a'}))
    dy = int(bool(app.keys & {'down', 's'})) - int(bool(app.keys & {'up', 'w'}))
    magnitude = math.hypot(dx, dy)
    speed = 8.0 if app.dashFrames > 0 else PLAYER_SPEED
    if magnitude:
        app.playerX = clamp(oldX + speed * dx / magnitude,
                            LEFT + PLAYER_RADIUS, RIGHT - PLAYER_RADIUS)
        app.playerY = clamp(oldY + speed * dy / magnitude,
                            MOVE_TOP + PLAYER_RADIUS, FINISH_Y)
        app.trail.append((oldX, oldY, 14 if app.dashFrames else 8))
    app.dashFrames = max(0, app.dashFrames - 1)
    app.progress = clamp((app.playerY - START_Y) / (FINISH_Y - START_Y), 0, 1)
    if moveGuards(app, oldX, oldY):
        app.tags += 1
        app.streak = 0
        app.consecutiveTags += 1
        if app.consecutiveTags >= 2:
            app.level = max(1, app.level - 1)
            app.consecutiveTags = 0
        app.state = 'tagged'
        app.delay = 65
        app.keys.clear()
        app.messageFrames = 0
        burst(app, app.playerX, app.playerY, CORAL, 24)
        return
    checkPasses(app)
    if app.playerY >= FINISH_Y:
        app.wins += 1
        app.streak += 1
        elapsed = app.roundFrames / app.stepsPerSecond
        best = app.bestTimes[app.roundLevel]
        if best is None or elapsed < best:
            app.bestTimes[app.roundLevel] = elapsed
        # Repeated lane crossings cannot farm points.
        app.lastScore = max(100, 1200 - int(elapsed * 35) - app.dashesUsed * 25)
        app.bestScores[app.roundLevel] = max(app.bestScores[app.roundLevel], app.lastScore)
        app.level = min(5, app.level + 1)
        app.consecutiveTags = 0
        app.state = 'won'
        app.keys.clear()
        for x in (220, 450, 680):
            burst(app, x, BOTTOM - 35, GOLD, 28)


def onStep(app):
    if app.state in ('paused', 'help'):
        return
    app.animationTick += 1
    updateEffects(app)
    if app.state == 'playing':
        advanceGame(app)
    elif app.state == 'countdown':
        app.countdown -= 1
        if app.countdown <= 0:
            app.state = 'playing'
    elif app.state == 'tagged':
        app.delay -= 1
        if app.delay <= 0:
            startRound(app)


def showHelp(app):
    if app.state == 'help':
        app.state = app.helpReturn
    else:
        app.helpReturn = app.state
        app.state = 'help'
    app.keys.clear()


def onKeyPress(app, key):
    key = key.lower()
    if key == 'h':
        showHelp(app)
    elif app.state == 'help':
        if key in ('enter', 'escape'):
            showHelp(app)
    elif key == 'm':
        resetRound(app)
        app.state = 'ready'
    elif key == 'r' and app.state != 'ready':
        startRound(app)
    elif key == 'enter' and app.state in ('ready', 'won'):
        startRound(app)
    elif key in ('p', 'escape'):
        if app.state in ('playing', 'countdown'):
            app.pauseReturn = app.state
            app.state = 'paused'
            app.keys.clear()
        elif app.state == 'paused':
            app.state = app.pauseReturn
    elif app.state == 'playing':
        if key == 'space':
            if app.cooldown == 0 and app.dashFrames == 0:
                app.dashFrames = DASH_DURATION
                app.cooldown = DASH_COOLDOWN
                app.dashesUsed += 1
        else:
            app.keys.add(key)


def onKeyRelease(app, key):
    app.keys.discard(key.lower())


def onKeyHold(app, keys):
    if app.state == 'playing':
        app.keys = {key.lower() for key in keys
                    if key.lower() in ('left', 'right', 'up', 'down', 'w', 'a', 's', 'd')}


def inside(x, y, left, top, width, height):
    return left <= x <= left + width and top <= y <= top + height


def onMousePress(app, mouseX, mouseY):
    if app.state == 'ready':
        if inside(mouseX, mouseY, 260, 548, 380, 52):
            startRound(app)
        elif inside(mouseX, mouseY, 260, 612, 380, 30):
            showHelp(app)
    elif app.state == 'help':
        if inside(mouseX, mouseY, 300, 610, 300, 45):
            showHelp(app)
    elif app.state == 'won':
        if inside(mouseX, mouseY, 280, 548, 340, 48):
            startRound(app)
    elif app.state == 'paused':
        if inside(mouseX, mouseY, 280, 548, 340, 48):
            app.state = app.pauseReturn


def label(text, x, y, size=14, color=CREAM, **kwargs):
    drawLabel(text, x, y, size=size, fill=color, **kwargs)


def button(text, x, y, width, height, selected=False):
    drawRect(x, y, width, height, fill=TEAL if selected else PANEL,
             border=TEAL if selected else EDGE, borderWidth=1)
    label(text, x + width / 2, y + height / 2, 15,
          BG if selected else CREAM, bold=True)


def drawPerson(app, x, y, color, runner=False, index=0):
    radius = PLAYER_RADIUS if runner else GUARD_RADIUS
    drawCircle(x, y + 5, radius + 3, fill='black', opacity=18)
    bob = math.sin(app.animationTick / 6 + index) * 1.5
    drawLine(x - 6, y + 10, x - 9, y + 18 + bob, fill=color, lineWidth=3)
    drawLine(x + 6, y + 10, x + 9, y + 18 - bob, fill=color, lineWidth=3)
    drawCircle(x, y, radius, fill=color, border=BG, borderWidth=2)
    drawCircle(x - 4, y - 3, 2, fill=BG)
    drawCircle(x + 4, y - 3, 2, fill=BG)
    drawLine(x - 4, y + 5, x + 4, y + 5, fill=BG, lineWidth=2)
    if runner:
        drawCircle(x, y, 19, fill=None, border=TEAL, opacity=55)


def drawBackground(app):
    drawRect(0, 0, 900, 850, fill=BG)
    for y in range(245, 670, 32):
        for x in (110, 790):
            drawLine(x - 8, y, x, y + 8, fill=EDGE, lineWidth=2)
            drawLine(x, y + 8, x + 8, y, fill=EDGE, lineWidth=2)
    label('THE CROSSING', 150, 36, 11, GOLD, align='left', bold=True)
    label('JUNUBI RUN', 150, 72, 34, align='left', bold=True)
    label('Read the guards. Find your moment.', 150, 108, 13, MUTED, align='left')
    label('Inspired by your South Sudanese game rules', 750, 43, 11, MUTED, align='right')
    label('H  Help     M  Menu', 750, 78, 13, TEAL, align='right')
    stats = [('AUTO DIFFICULTY', f'LEVEL {app.roundLevel} / 5'),
             ('WINS / TAGS', f'{app.wins} / {app.tags}'),
             ('WIN STREAK', str(app.streak)),
             ('BEST AT THIS LEVEL', '--' if app.bestTimes[app.roundLevel] is None
              else f'{app.bestTimes[app.roundLevel]:.1f}s')]
    for i, (name, value) in enumerate(stats):
        x = 150 + i * 153
        drawRect(x, 135, 141, 56, fill=PANEL)
        label(name, x + 12, 150, 9, MUTED, align='left', bold=True)
        label(value, x + 12, 174, 18, align='left', bold=True)
    if app.messageFrames > 0:
        label(TAUNT, 450, 213, 15, TEAL, bold=True)
    else:
        label('YOU: MINT RUNNER', 150, 213, 11, TEAL, align='left', bold=True)
        label(f'TIME  {app.roundFrames / 60:.1f}s', 750, 213, 12, align='right')


def drawCourt(app):
    drawRect(LEFT - 7, TOP - 7, RIGHT - LEFT + 14, BOTTOM - TOP + 14,
             fill=PANEL, border=EDGE)
    drawRect(LEFT, TOP, RIGHT - LEFT, BOTTOM - TOP, fill=FIELD)
    for row in range(5):
        for col in range(9):
            drawCircle(LEFT + 30 + col * 66, TOP + 30 + row * 70,
                       1, fill=CREAM, opacity=10)
    drawRect(LEFT, MOVE_TOP, RIGHT - LEFT, TOP - MOVE_TOP, fill=TEAL, opacity=8)
    drawRect(LEFT, BOTTOM, RIGHT - LEFT, MOVE_BOTTOM - BOTTOM + 10,
             fill=GOLD, opacity=17)
    label('START', LEFT + 16, START_Y, 10, TEAL, align='left', bold=True)
    label('FINISH', LEFT + 16, FINISH_Y, 10, GOLD, align='left', bold=True)
    drawLine(LEFT, FINISH_Y + PLAYER_RADIUS, RIGHT, FINISH_Y + PLAYER_RADIUS,
             fill=GOLD, lineWidth=2, dashes=True)
    drawLine(CENTER, TOP, CENTER, BOTTOM, fill=GOLD, lineWidth=9, opacity=12)
    drawLine(CENTER, TOP, CENTER, BOTTOM, fill=GOLD, lineWidth=2, opacity=65)
    for index, y in enumerate(ALL_HORIZONTAL_LINES):
        drawLine(LEFT, y, RIGHT, y, fill=CORAL, lineWidth=9, opacity=12)
        drawLine(LEFT, y, RIGHT, y, fill=CORAL, lineWidth=2, opacity=65)
        for x in (LEFT, RIGHT):
            drawCircle(x, y, 4, fill=CORAL)
        laneName = ('S', '1', '2', 'F')[index]
        label(laneName, LEFT - 23, y, 12, CORAL, bold=True)
    for y in (TOP, BOTTOM):
        drawCircle(CENTER, y, 4, fill=GOLD)
    for x, y, life in app.trail:
        drawCircle(x, y, 7, fill=TEAL, opacity=clamp(life * 3, 0, 42))
    for index, guard in enumerate(app.guards):
        drawPerson(app, guard['x'], guard['y'], guard['color'], index=index)
        gx, gy = guard['x'], guard['y']
        if guard['axis'] == 'vertical':
            drawLine(gx, gy - 26, gx, gy - 20, fill=GOLD, lineWidth=2)
        else:
            drawLine(gx - 4, gy - 24, gx + 4, gy - 24, fill=CORAL, lineWidth=2)
    drawPerson(app, app.playerX, app.playerY, TEAL, runner=True)
    for p in app.particles:
        drawCircle(p['x'], p['y'], 3, fill=p['color'], opacity=clamp(p['life'] * 3, 0, 100))


def drawFooter(app):
    label('CROSSING', 150, 712, 10, MUTED, align='left', bold=True)
    drawRect(233, 707, 267, 9, fill=PANEL)
    if app.progress > 0:
        drawRect(233, 707, max(1, 267 * app.progress), 9, fill=TEAL)
    label(f'{int(app.progress * 100)}%', 515, 712, 11, TEAL, align='left')
    ready = app.cooldown == 0
    label('DASH READY' if ready else f'DASH  {app.cooldown / 60:.1f}s',
          750, 712, 11, TEAL if ready else MUTED, align='right', bold=True)
    drawRect(610, 732, 140, 4, fill=PANEL)
    charge = 1 - app.cooldown / DASH_COOLDOWN
    if charge > 0:
        drawRect(610, 732, max(1, 140 * charge), 4, fill=TEAL)
    label('ARROWS / WASD  Move      SPACE  Dash      P  Pause      R  Retry', 450, 762, 13)
    label('Dash gives speed, not protection. A touch sends you back to the top.',
          450, 791, 12, MUTED)
    label('Session records only. One player at a time; take turns with friends.', 450, 821, 11, MUTED)


def overlay():
    drawRect(0, 122, 900, 570, fill=BG, opacity=78)
    drawRect(175, 255, 550, 407, fill=PANEL, border=EDGE)
    drawRect(175, 255, 550, 4, fill=GOLD)


def drawMenu(app):
    overlay()
    label('OUTSMART THE LINE GUARDS', 450, 292, 11, GOLD, bold=True)
    label('Make your crossing.', 450, 333, 31, bold=True)
    label('You are the mint runner. Reach the bottom to win.', 450, 376, 15)
    label('Five guards: start, finish, two inside, and the center.', 450, 404, 14, MUTED)
    label(f'AUTOMATIC DIFFICULTY  /  LEVEL {app.level} OF 5', 450, 449, 12, TEAL, bold=True)
    label('Win: next level. Two tags in a row: one level easier.', 450, 485, 13, MUTED)
    label('Guard speed stays steady during each crossing.', 450, 511, 12, MUTED)
    button('START CROSSING  /  ENTER', 260, 548, 380, 52, True)
    label('HOW TO PLAY  /  H', 450, 627, 12, TEAL, bold=True)


def drawHelp(app):
    drawRect(0, 122, 900, 570, fill=BG, opacity=90)
    drawRect(175, 201, 550, 475, fill=PANEL, border=EDGE)
    label('HOW TO PLAY', 450, 240, 28, bold=True)
    lines = [
        ('01   PASS ALL THE WAY THROUGH', 'Start above the court. Finish below the last guard.'),
        ('02   FIVE GUARDS, EACH ON HIS OWN LINE', 'Four move sideways. The center guard moves vertically.'),
        ('03   DIFFICULTY ADAPTS TO YOU', 'Win: level up. Two tags in a row: one level easier.'),
        ('04   DASH AT THE RIGHT MOMENT', 'Hold a direction + SPACE. Recharges in 3 seconds.'),
        ('05   A TOUCH MEANS TRY AGAIN', 'No lives limit. Dash does not make you invincible.')]
    for index, (title, detail) in enumerate(lines):
        y = 293 + index * 59
        label(title, 205, y, 11, TEAL, align='left', bold=True)
        label(detail, 205, y + 23, 13, align='left')
    button('GOT IT  /  ENTER', 300, 610, 300, 45, True)


def drawState(app):
    if app.state == 'ready':
        drawMenu(app)
    elif app.state == 'help':
        drawHelp(app)
    elif app.state == 'countdown':
        drawRect(310, 395, 280, 115, fill=BG, opacity=90, border=EDGE)
        label(str(math.ceil(app.countdown / 60)), 450, 434, 42, TEAL, bold=True)
        label('GET READY TO CROSS', 450, 483, 11, bold=True)
    elif app.state in ('paused', 'won', 'tagged'):
        overlay()
        if app.state == 'paused':
            label('Take a breath.', 450, 342, 31, bold=True)
            label('The clock and guards are paused.', 450, 406, 15, MUTED)
            label('H: Help      M: Menu      R: Restart', 450, 455, 13, MUTED)
            button('CONTINUE  /  P', 280, 548, 340, 48, True)
        elif app.state == 'tagged':
            label('Tagged!', 450, 342, 37, CORAL, bold=True)
            label('Try drawing a guard one way, then go the other.', 450, 406, 14)
            label('Returning to the top...', 450, 477, 15, TEAL, bold=True)
            label(f'Next attempt: level {app.level} / 5     R: Retry now', 450, 578, 12, MUTED)
        else:
            label('You made it!', 450, 327, 37, GOLD, bold=True)
            label(f'{app.lastScore} POINTS', 450, 378, 25, TEAL, bold=True)
            label(f'Level {app.roundLevel}  /  {app.roundFrames / 60:.2f} seconds'
                  f'  /  {app.dashesUsed} dashes', 450, 424, 15)
            label(f'Best at this level: {app.bestScores[app.roundLevel]} points', 450, 464, 13, MUTED)
            label(f'Next crossing: level {app.level} / 5', 450, 501, 13, TEAL)
            button('CROSS AGAIN  /  ENTER', 280, 548, 340, 48, True)
            label('M: Menu     H: Help', 450, 627, 12, MUTED)


def redrawAll(app):
    drawBackground(app)
    drawCourt(app)
    drawFooter(app)
    drawState(app)
    if app.state == 'won':
        for p in app.particles:
            drawCircle(p['x'], p['y'], 3, fill=p['color'],
                       opacity=clamp(p['life'] * 3, 0, 100))


def main():
    runApp(width=900, height=850)


if __name__ == '__main__':
    main()
