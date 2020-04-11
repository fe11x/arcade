"""
Defender Clone.

This example shows how to:
1. Create a mini-map
2. Create a 'bloom' or 'glow' effect.

If Python and Arcade are installed, this example can be run from the command line with:
python -m arcade.examples.defender
"""

import arcade
import os
import random

# --- Minimap Related ---
from arcade.experimental import geometry

# --- Bloom related ---
from arcade.experimental import postprocessing
import pyglet.gl as gl

# Size/title of the window
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Defender Clone"

# Size of the playing field
PLAYING_FIELD_WIDTH = 5000
PLAYING_FIELD_HEIGHT = 800

# Size of the minimap
MINIMAP_HEIGHT = SCREEN_HEIGHT / 4

# Size of the playing field.
# This, plus the minimap height, should add up to the height of the screen.
MAIN_SCREEN_HEIGHT = SCREEN_HEIGHT - MINIMAP_HEIGHT

# How far away from the edges do we get before scrolling?
VIEWPORT_MARGIN = SCREEN_WIDTH / 2 - 50
TOP_VIEWPORT_MARGIN = 30
DEFAULT_BOTTOM_VIEWPORT = -10

# Control the physics of how the player moves
MAX_HORIZONTAL_MOVEMENT_SPEED = 10
MAX_VERTICAL_MOVEMENT_SPEED = 5
HORIZONTAL_ACCELERATION = 0.5
VERTICAL_ACCELERATION = 0.2
MOVEMENT_DRAG = 0.08

# How far the bullet travels before disappearing
BULLET_MAX_DISTANCE = SCREEN_WIDTH * 0.75

class Player(arcade.SpriteSolidColor):
    """ Player ship """
    def __init__(self):
        """ Set up player """
        super().__init__(40, 10, arcade.color.SLATE_GRAY)
        self.face_right = True

    def accelerate_up(self):
        """ Accelerate player up """
        self.change_y += VERTICAL_ACCELERATION
        if self.change_y > MAX_VERTICAL_MOVEMENT_SPEED:
            self.change_y = MAX_VERTICAL_MOVEMENT_SPEED

    def accelerate_down(self):
        """ Accelerate player down """
        self.change_y -= VERTICAL_ACCELERATION
        if self.change_y < -MAX_VERTICAL_MOVEMENT_SPEED:
            self.change_y = -MAX_VERTICAL_MOVEMENT_SPEED

    def accelerate_right(self):
        """ Accelerate player right """
        self.face_right = True
        self.change_x += HORIZONTAL_ACCELERATION
        if self.change_x > MAX_HORIZONTAL_MOVEMENT_SPEED:
            self.change_x = MAX_HORIZONTAL_MOVEMENT_SPEED

    def accelerate_left(self):
        """ Accelerate player left """
        self.face_right = False
        self.change_x -= HORIZONTAL_ACCELERATION
        if self.change_x < -MAX_HORIZONTAL_MOVEMENT_SPEED:
            self.change_x = -MAX_HORIZONTAL_MOVEMENT_SPEED

    def update(self):
        """ Move the player """
        # Move
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Drag
        if self.change_x > 0:
            self.change_x -= MOVEMENT_DRAG
        if self.change_x < 0:
            self.change_x += MOVEMENT_DRAG
        if abs(self.change_x) < MOVEMENT_DRAG:
            self.change_x = 0

        if self.change_y > 0:
            self.change_y -= MOVEMENT_DRAG
        if self.change_y < 0:
            self.change_y += MOVEMENT_DRAG
        if abs(self.change_y) < MOVEMENT_DRAG:
            self.change_y = 0

        # Check bounds
        if self.left < 0:
            self.left = 0
        elif self.right > PLAYING_FIELD_WIDTH - 1:
            self.right = PLAYING_FIELD_WIDTH - 1

        if self.bottom < 0:
            self.bottom = 0
        elif self.top > SCREEN_HEIGHT - 1:
            self.top = SCREEN_HEIGHT - 1

class Bullet(arcade.SpriteSolidColor):
    """ Bullet """

    def __init__(self, width, height, color):
        super().__init__(width, height, color)
        self.distance = 0

    def update(self):
        """ Move the particle, and fade out """
        # Move
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.distance += self.change_x
        if self.distance > BULLET_MAX_DISTANCE:
            self.remove_from_sprite_lists()

class Particle(arcade.SpriteSolidColor):
    """ Particle from explosion """
    def update(self):
        """ Move the particle, and fade out """
        # Move
        self.center_x += self.change_x
        self.center_y += self.change_y
        # Fade
        self.alpha -= 5
        if self.alpha <= 0:
            self.remove_from_sprite_lists()

class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self, width, height, title):
        """ Initializer """

        # Call the parent class initializer
        super().__init__(width, height, title)

        # Set the working directory (where we expect to find files) to the same
        # directory this .py file is in. You can leave this out of your own
        # code, but it is needed to easily run the examples using "python -m"
        # as mentioned at the top of this program.
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

        # Variables that will hold sprite lists
        self.player_list = None
        self.star_sprite_list = None
        self.enemy_sprite_list = None
        self.bullet_sprite_list = None

        # Set up the player info
        self.player_sprite = None

        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        self.view_bottom = 0
        self.view_left = 0

        # Set the background color
        arcade.set_background_color(arcade.color.BLACK)

        # --- Mini-map related ---
        self.minimap_color_attachment = None
        self.minimap_screen = None
        self.quad_fs = None
        self.mini_map_quad = None

        program = self.ctx.load_program("simple_shader.vert", "simple_shader.frag")
        self.minimap_color_attachment = self.ctx.texture((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.minimap_screen = self.ctx.framebuffer(color_attachments=[self.minimap_color_attachment])
        self.play_screen_color_attachment = self.ctx.texture((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.play_screen = self.ctx.framebuffer(color_attachments=[self.play_screen_color_attachment])
        self.mini_map_quad = geometry.quad_fs(program, size=(2.0, 0.5), pos=(0.0, 0.75))
        self.play_screen_quad = geometry.quad_fs(program, size=(2.0, 1.5), pos=(0.0, 0.0))

        # --- Bloom related ---
        self.glow = postprocessing.Glow((SCREEN_WIDTH // 8, SCREEN_HEIGHT // 8))

    def setup(self):
        """ Set up the game and initialize the variables. """

        # Sprite lists
        self.player_list = arcade.SpriteList()
        self.star_sprite_list = arcade.SpriteList()
        self.enemy_sprite_list = arcade.SpriteList()
        self.bullet_sprite_list = arcade.SpriteList()

        # Set up the player
        self.player_sprite = Player()
        self.player_sprite.center_x = 50
        self.player_sprite.center_y = 50
        self.player_list.append(self.player_sprite)

        # Add stars
        for i in range(80):
            sprite = arcade.SpriteSolidColor(4, 4, arcade.color.WHITE)
            sprite.center_x = random.randrange(PLAYING_FIELD_WIDTH)
            sprite.center_y = random.randrange(600)
            self.star_sprite_list.append(sprite)

        # Add enemies
        for i in range(20):
            sprite = arcade.SpriteSolidColor(20, 20, arcade.csscolor.LIGHT_SALMON)
            sprite.center_x = random.randrange(PLAYING_FIELD_WIDTH)
            sprite.center_y = random.randrange(600)
            self.enemy_sprite_list.append(sprite)

    def on_draw(self):
        """ Render the screen. """
        try:
            # This command has to happen before we start drawing
            arcade.start_render()

            # Draw to the frame buffer used in the minimap
            self.minimap_screen.use()
            self.minimap_screen.clear()

            arcade.set_viewport(0,
                                PLAYING_FIELD_WIDTH,
                                0,
                                SCREEN_HEIGHT)

            self.enemy_sprite_list.draw()
            self.player_list.draw()

            # Draw to the 'glow' layer
            self.play_screen.use()
            self.play_screen.clear()

            # self.use()

            arcade.set_viewport(self.view_left,
                                SCREEN_WIDTH + self.view_left,
                                self.view_bottom,
                                SCREEN_HEIGHT + self.view_bottom)

            # Draw all the sprites on the screen
            self.star_sprite_list.draw()
            self.bullet_sprite_list.draw()

            # Draw the ground
            arcade.draw_line(0, 0, PLAYING_FIELD_WIDTH, 0, arcade.color.WHITE)

            # Now draw to the actual screen
            self.use()

            arcade.set_viewport(self.view_left,
                                SCREEN_WIDTH + self.view_left,
                                self.view_bottom,
                                SCREEN_HEIGHT + self.view_bottom)

            gl.glDisable(gl.GL_BLEND)
            self.glow.render(self.play_screen_color_attachment, self)
            gl.glEnable(gl.GL_BLEND)

            self.enemy_sprite_list.draw()
            self.player_list.draw()

            # Draw the ground
            arcade.draw_line(0, 0, PLAYING_FIELD_WIDTH, 0, arcade.color.WHITE)

            # Draw a background for the minimap
            arcade.draw_rectangle_filled(SCREEN_WIDTH - SCREEN_WIDTH / 2 + self.view_left,
                                         SCREEN_HEIGHT - SCREEN_HEIGHT / 8 + self.view_bottom,
                                         SCREEN_WIDTH,
                                         SCREEN_HEIGHT / 4,
                                         arcade.color.DARK_GREEN)

            # Draw the minimap
            self.minimap_color_attachment.use(0)
            self.mini_map_quad.render()

            # Draw a rectangle showing where the screen is
            width_ratio = SCREEN_WIDTH / PLAYING_FIELD_WIDTH
            height_ratio = MINIMAP_HEIGHT / PLAYING_FIELD_HEIGHT
            width = width_ratio * SCREEN_WIDTH
            height = height_ratio * MAIN_SCREEN_HEIGHT
            x = (self.view_left + SCREEN_WIDTH / 2) * width_ratio + self.view_left
            y = self.view_bottom + height / 2 + (SCREEN_HEIGHT - MINIMAP_HEIGHT) + self.view_bottom * height_ratio

            arcade.draw_rectangle_outline(center_x=x, center_y=y,
                                          width=width, height=height,
                                          color=arcade.color.WHITE)

        except Exception:
            import traceback
            traceback.print_exc()

    def on_update(self, delta_time):
        """ Movement and game logic """

        # Calculate speed based on the keys pressed
        if self.up_pressed and not self.down_pressed:
            self.player_sprite.accelerate_up()
        elif self.down_pressed and not self.up_pressed:
            self.player_sprite.accelerate_down()

        if self.left_pressed and not self.right_pressed:
            self.player_sprite.accelerate_left()
        elif self.right_pressed and not self.left_pressed:
            self.player_sprite.accelerate_right()

        # Call update to move the sprite
        self.player_list.update()
        self.bullet_sprite_list.update()

        for bullet in self.bullet_sprite_list:
            enemy_hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_sprite_list)
            for enemy in enemy_hit_list:
                enemy.remove_from_sprite_lists()
                for i in range(10):
                    particle = Particle(4, 4, arcade.color.RED)
                    while particle.change_y == 0 and particle.change_x == 0:
                        particle.change_y = random.randrange(-2, 3)
                        particle.change_x = random.randrange(-2, 3)
                        particle.center_x = enemy.center_x
                        particle.center_y = enemy.center_y
                        self.bullet_sprite_list.append(particle)

        # Scroll left
        left_boundary = self.view_left + VIEWPORT_MARGIN
        if self.player_sprite.left < left_boundary:
            self.view_left -= left_boundary - self.player_sprite.left

        # Scroll right
        right_boundary = self.view_left + SCREEN_WIDTH - VIEWPORT_MARGIN
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary

        # Scroll up
        self.view_bottom = DEFAULT_BOTTOM_VIEWPORT
        top_boundary = self.view_bottom + SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN - MINIMAP_HEIGHT
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary

        self.view_left = int(self.view_left)
        self.view_bottom = int(self.view_bottom)

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if key == arcade.key.UP:
            self.up_pressed = True
        elif key == arcade.key.DOWN:
            self.down_pressed = True
        elif key == arcade.key.LEFT:
            self.left_pressed = True
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
        elif key == arcade.key.SPACE:
            # Shoot out a bullet/laser
            bullet = arcade.SpriteSolidColor(35, 3, arcade.color.WHITE)
            bullet.center_x = self.player_sprite.center_x
            bullet.center_y = self.player_sprite.center_y
            bullet.change_x = max(12, abs(self.player_sprite.change_x) + 10)

            if not self.player_sprite.face_right:
                bullet.change_x *= -1

            self.bullet_sprite_list.append(bullet)

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        if key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.down_pressed = False
        elif key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False


def main():
    """ Main method """
    window = MyGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
