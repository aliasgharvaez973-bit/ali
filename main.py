from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, BooleanProperty, StringProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.metrics import dp

# امتیازی که با رسیدن بهش بازی تموم می‌شه
WIN_SCORE = 5
# حداکثر و حداقل سرعت مجاز توپ
MAX_BALL_SPEED = 16
MIN_BALL_SPEED = 4
# چقدر سرعت حرکت راکت روی سرعت توپ بعد از ضربه تاثیر بذاره
PADDLE_POWER_FACTOR = 0.5
# فاصله‌ی اضافه (به پیکسل) که لمس در اطراف راکت هم قبول بشه، برای راحتی گرفتن راکت با انگشت
TOUCH_MARGIN = 30
# نصف ارتفاع دروازه (تقریبا معادل ۴ سانتی‌متر کل ارتفاع دروازه)
GOAL_HALF_HEIGHT = dp(126)


class PongPaddle(Widget):
    score = NumericProperty(0)
    # سرعت فعلی حرکت راکت (پیکسل بر فریم) — برای فیزیک ضربه
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    # این راکت سمت چپه یا راست؟ جهت "جلوی" راکت رو مشخص می‌کنه
    is_left_paddle = BooleanProperty(True)
    # جلوگیری از چند بار ضربه خوردن پشت سر هم در یک تماس
    _already_colliding = False

    def front_x(self):
        # جلوی راکت چپ سمت راستشه (لبه‌ای که رو به زمین بازیه)
        # جلوی راکت راست سمت چپشه
        return self.right if self.is_left_paddle else self.x

    def bounce_ball(self, ball, prev_ball_x):
        # فقط وقتی توپ داره به این راکت نزدیک می‌شه بررسی کن، نه وقتی داره دور می‌شه
        approaching = (ball.velocity_x < 0) if self.is_left_paddle else (ball.velocity_x > 0)
        if not approaching:
            self._already_colliding = False
            return

        front = self.front_x()

        # آیا توپ دقیقا امسال از "جلوی" راکت عبور کرد؟ (نه از پهلو یا پشت)
        if self.is_left_paddle:
            crossed_front = prev_ball_x >= front and ball.x <= front
        else:
            prev_leading = prev_ball_x + ball.width
            curr_leading = ball.x + ball.width
            crossed_front = prev_leading <= front and curr_leading >= front

        touching_now = self.collide_widget(ball)
        vertical_overlap = (ball.top > self.y) and (ball.y < self.top)

        should_bounce = (crossed_front or touching_now) and vertical_overlap and not self._already_colliding

        if not should_bounce:
            self._already_colliding = touching_now
            return

        self._already_colliding = True

        vx, vy = ball.velocity
        offset = (ball.center_y - self.center_y) / (self.height / 2)

        base_vx = -vx
        base_vy = vy + offset

        # اضافه کردن قدرت ضربه بر اساس سرعت حرکت راکت در لحظه‌ی برخورد
        power_x = self.velocity_x * PADDLE_POWER_FACTOR
        power_y = self.velocity_y * PADDLE_POWER_FACTOR

        new_vx = base_vx + power_x
        new_vy = base_vy + power_y

        # مطمئن می‌شیم جهت افقی توپ همیشه به سمت مخالف راکت باشه (که برنگرده)
        if base_vx > 0 and new_vx < 1:
            new_vx = 1
        elif base_vx < 0 and new_vx > -1:
            new_vx = -1

        new_vel = Vector(new_vx, new_vy)
        speed = new_vel.length()

        if speed > MAX_BALL_SPEED:
            new_vel = new_vel.normalize() * MAX_BALL_SPEED
        elif speed < MIN_BALL_SPEED:
            new_vel = new_vel.normalize() * MIN_BALL_SPEED

        ball.velocity = new_vel.x, new_vel.y

        # توپ رو دقیقا جلوی راکت می‌ذاریم تا داخل راکت گیر نکنه یا از پشتش دوباره برخورد نکنه
        if self.is_left_paddle:
            ball.x = front
        else:
            ball.x = front - ball.width


class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class PongGame(Widget):
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)

    is_running = BooleanProperty(False)
    is_game_over = BooleanProperty(False)
    pause_text = StringProperty("Pause")
    winner_text = StringProperty("")
    goal_half_height = NumericProperty(GOAL_HALF_HEIGHT)

    _clock_event = None

    def reset_paddle_positions(self):
        self.player1.center = (self.x + self.width / 4, self.center_y)
        self.player2.center = (self.right - self.width / 4, self.center_y)
        for paddle in (self.player1, self.player2):
            paddle.velocity_x = 0
            paddle.velocity_y = 0
            paddle._last_center_x = paddle.center_x
            paddle._last_center_y = paddle.center_y
            paddle._already_colliding = False

    def serve_ball(self, vel=(4, 0)):
        self.ball.center = self.center
        self.ball.velocity = vel

    def start_game(self):
        if self.is_game_over:
            self.player1.score = 0
            self.player2.score = 0
            self.winner_text = ""
            self.is_game_over = False

        if self.is_running:
            return

        self.reset_paddle_positions()
        self.serve_ball()
        self.is_running = True
        self.pause_text = "Pause"

        if self._clock_event is not None:
            self._clock_event.cancel()
        self._clock_event = Clock.schedule_interval(self.update, 1.0 / 60.0)

    def toggle_pause(self):
        if self.is_game_over or self._clock_event is None:
            return

        if self.is_running:
            self._clock_event.cancel()
            self.is_running = False
            self.pause_text = "Resume"
        else:
            self._clock_event = Clock.schedule_interval(self.update, 1.0 / 60.0)
            self.is_running = True
            self.pause_text = "Pause"

    def end_game(self, winner_side):
        if self._clock_event is not None:
            self._clock_event.cancel()
            self._clock_event = None
        self.is_running = False
        self.is_game_over = True
        self.winner_text = "LEFT WIN" if winner_side == "left" else "RIGHT WIN"

    def _update_paddle_velocity(self, paddle):
        last_cx = getattr(paddle, "_last_center_x", paddle.center_x)
        last_cy = getattr(paddle, "_last_center_y", paddle.center_y)
        paddle.velocity_x = paddle.center_x - last_cx
        paddle.velocity_y = paddle.center_y - last_cy
        paddle._last_center_x = paddle.center_x
        paddle._last_center_y = paddle.center_y

    def update(self, dt):
        self._update_paddle_velocity(self.player1)
        self._update_paddle_velocity(self.player2)

        prev_ball_x = self.ball.x
        self.ball.move()

        if self.ball.y < 0 or self.ball.top > self.height:
            self.ball.velocity_y *= -1

        self.player1.bounce_ball(self.ball, prev_ball_x)
        self.player2.bounce_ball(self.ball, prev_ball_x)

        goal_top = self.center_y + self.goal_half_height
        goal_bottom = self.center_y - self.goal_half_height

        # توپ از لبه‌ی چپ رد شد
        if self.ball.x < self.x:
            if goal_bottom <= self.ball.center_y <= goal_top:
                self.player2.score += 1
                if self.player2.score >= WIN_SCORE:
                    self.end_game("right")
                    return
                self.serve_ball(vel=(4, 0))
            else:
                self.ball.x = self.x
                self.ball.velocity_x = abs(self.ball.velocity_x)

        # توپ از لبه‌ی راست رد شد
        if self.ball.x > self.width:
            if goal_bottom <= self.ball.center_y <= goal_top:
                self.player1.score += 1
                if self.player1.score >= WIN_SCORE:
                    self.end_game("left")
                    return
                self.serve_ball(vel=(-4, 0))
            else:
                self.ball.x = self.width - self.ball.width
                self.ball.velocity_x = -abs(self.ball.velocity_x)

    def _move_paddle(self, paddle, target_x, target_y, min_x, max_x):
        half_w = paddle.width / 2
        half_h = paddle.height / 2

        new_center_x = max(min_x + half_w, min(target_x, max_x - half_w))
        new_center_y = max(self.y + half_h, min(target_y, self.top - half_h))

        paddle.center = (new_center_x, new_center_y)

    def _touch_hits_paddle(self, paddle, touch):
        return (paddle.x - TOUCH_MARGIN) <= touch.x <= (paddle.right + TOUCH_MARGIN) and \
               (paddle.y - TOUCH_MARGIN) <= touch.y <= (paddle.top + TOUCH_MARGIN)

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True

        if self.is_game_over:
            App.get_running_app().go_to_start()
            return True

        if not self.is_running:
            return False

        if self._touch_hits_paddle(self.player1, touch):
            touch.grab(self)
            touch.ud["paddle"] = self.player1
            return True

        if self._touch_hits_paddle(self.player2, touch):
            touch.grab(self)
            touch.ud["paddle"] = self.player2
            return True

        return False

    def on_touch_move(self, touch):
        if touch.grab_current is not self or "paddle" not in touch.ud:
            return

        paddle = touch.ud["paddle"]

        if paddle is self.player1:
            self._move_paddle(paddle, touch.x, touch.y, self.x, self.center_x)
        else:
            self._move_paddle(paddle, touch.x, touch.y, self.center_x, self.right)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)


class StartScreen(Screen):
    pass


class GameScreen(Screen):
    pass


class PongApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StartScreen(name="start"))
        sm.add_widget(GameScreen(name="game"))
        sm.current = "start"
        return sm

    def go_to_game(self):
        self.root.current = "game"
        game_screen = self.root.get_screen("game")
        game_screen.ids.pong_widget.start_game()

    def go_to_start(self):
        self.root.current = "start"


if __name__ == '__main__':
    PongApp().run()
