"""
Pygame으로 만든 테트리스 게임

조작법:
  - 좌/우 화살표 : 블록 좌우 이동
  - 위 화살표    : 블록 시계방향 회전
  - 아래 화살표  : 블록 한 칸씩 아래로 이동 (소프트 드롭)
  - 스페이스바   : 블록 바로 아래로 떨어뜨리기 (하드 드롭)
  - ESC          : 게임 종료
"""

import pygame
import random
import sys
import numpy as np

# ------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------
COLS = 10                # 보드 가로 칸 수
ROWS = 20                # 보드 세로 칸 수
CELL_SIZE = 30            # 셀 하나의 픽셀 크기

BOARD_WIDTH = COLS * CELL_SIZE
BOARD_HEIGHT = ROWS * CELL_SIZE

SIDE_PANEL_WIDTH = 200    # 다음 블록, 점수 표시할 오른쪽 패널
SCREEN_WIDTH = BOARD_WIDTH + SIDE_PANEL_WIDTH
SCREEN_HEIGHT = BOARD_HEIGHT

FPS = 60

# 낙하 속도 (밀리초 단위, 값이 작을수록 빨리 떨어짐)
BASE_FALL_SPEED = 700

# ------------------------------------------------------------
# 색상 정의
# ------------------------------------------------------------
BLACK = (10, 10, 20)
WHITE = (240, 240, 240)
GRAY = (60, 60, 70)
GRID_COLOR = (40, 40, 50)

# 테트로미노별 색상
COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

# ------------------------------------------------------------
# 테트로미노 모양 정의 (4x4 매트릭스 기준의 좌표 리스트)
# 각 모양은 (row, col) 좌표들의 리스트로 표현하고,
# 회전은 좌표를 재계산하는 방식으로 처리한다.
# ------------------------------------------------------------
SHAPES = {
    'I': [(0, 0), (0, 1), (0, 2), (0, 3)],
    'O': [(0, 0), (0, 1), (1, 0), (1, 1)],
    'T': [(0, 0), (0, 1), (0, 2), (1, 1)],
    'S': [(1, 0), (1, 1), (0, 1), (0, 2)],
    'Z': [(0, 0), (0, 1), (1, 1), (1, 2)],
    'J': [(0, 0), (1, 0), (1, 1), (1, 2)],
    'L': [(0, 2), (1, 0), (1, 1), (1, 2)],
}


class SoundManager:
    """
    별도 음원 파일 없이 numpy로 파형을 직접 만들어서
    pygame.mixer.Sound 객체로 변환해주는 클래스.
    사인파 + 짧은 페이드아웃으로 '삐' 하는 효과음을 생성한다.
    """

    SAMPLE_RATE = 44100

    def __init__(self):
        self.enabled = True
        try:
            pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
        except pygame.error:
            # 오디오 장치가 없는 환경(서버, 헤드리스 등)에서는 조용히 비활성화
            self.enabled = False
            return

        self.sounds = {
            "move": self._make_tone(220, 0.05, volume=0.25),
            "rotate": self._make_tone(330, 0.06, volume=0.25),
            "drop": self._make_tone(150, 0.12, volume=0.35),
            "line_clear": self._make_chord([523, 659, 784], 0.20, volume=0.4),
            "level_up": self._make_chord([392, 523, 659, 784], 0.30, volume=0.4),
            "game_over": self._make_tone(110, 0.6, volume=0.4, descending=True),
        }

    def _make_tone(self, freq, duration, volume=0.3, descending=False):
        """단일 주파수의 사인파 톤 생성 (descending=True면 음이 점점 낮아짐)"""
        n_samples = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)

        if descending:
            # 시간에 따라 주파수가 절반까지 떨어지도록
            freq_curve = freq * (1 - 0.5 * (t / duration))
            wave = np.sin(2 * np.pi * freq_curve * t)
        else:
            wave = np.sin(2 * np.pi * freq * t)

        return self._to_sound(wave, volume)

    def _make_chord(self, freqs, duration, volume=0.3):
        """여러 주파수를 합쳐서 화음 느낌의 효과음 생성 (줄 삭제, 레벨업용)"""
        n_samples = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)

        wave = np.zeros(n_samples)
        for freq in freqs:
            wave += np.sin(2 * np.pi * freq * t)
        wave /= len(freqs)  # 합친 만큼 커진 진폭을 다시 정규화

        return self._to_sound(wave, volume)

    def _to_sound(self, wave, volume):
        """0~1 범위의 파형 배열을 pygame Sound 객체로 변환 (짧은 페이드아웃 포함)"""
        n_samples = len(wave)

        # 끝부분에 짧은 페이드아웃을 걸어서 '뚝' 끊기는 잡음을 방지
        fade_len = max(1, int(n_samples * 0.15))
        fade = np.linspace(1, 0, fade_len)
        wave[-fade_len:] *= fade

        audio = (wave * volume * 32767).astype(np.int16)

        # 믹서가 실제로 몇 채널로 초기화됐는지 확인해서 배열 형태를 맞춘다
        # (일부 환경에서는 mono 요청해도 stereo로 초기화되는 경우가 있음)
        init_info = pygame.mixer.get_init()
        channels = init_info[2] if init_info else 1

        if channels >= 2:
            audio = np.repeat(audio.reshape(-1, 1), channels, axis=1)

        audio = np.ascontiguousarray(audio)
        return pygame.sndarray.make_sound(audio)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()


class Piece:
    """떨어지는 블록(테트로미노)을 표현하는 클래스"""

    def __init__(self, shape_key):
        self.shape_key = shape_key
        self.color = COLORS[shape_key]
        # 좌표를 (row, col) 튜플의 리스트로 복사
        self.cells = [list(pos) for pos in SHAPES[shape_key]]
        # 보드 위쪽 중앙에서 시작하도록 오프셋 설정
        self.row_offset = 0
        self.col_offset = COLS // 2 - 2

    def get_cells(self):
        """현재 위치 기준 실제 보드 좌표 리스트 반환"""
        return [(r + self.row_offset, c + self.col_offset) for r, c in self.cells]

    def rotate_cells(self):
        """시계방향 회전된 좌표 리스트를 반환 (실제 적용은 하지 않음)"""
        if self.shape_key == 'O':
            # 정사각형은 회전해도 모양이 같음
            return [list(pos) for pos in self.cells]

        # 4x4 그리드 기준으로 시계방향 회전: (r, c) -> (c, 3 - r)
        rotated = [[c, 3 - r] for r, c in self.cells]
        return rotated


class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("테트리스")
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("malgungothic", 36)
        self.font_small = pygame.font.SysFont("malgungothic", 22)

        self.sound = SoundManager()

        self.reset_game()

    def reset_game(self):
        # board[row][col] = None 이면 빈 칸, 아니면 색상 값 저장
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]

        self.bag = []
        self.current = self.spawn_piece()
        self.next_piece = self.spawn_piece()

        self.score = 0
        self.lines_cleared_total = 0
        self.level = 1
        self.game_over = False

        self.fall_time = 0
        self.fall_speed = BASE_FALL_SPEED

    def get_next_shape_key(self):
        """7-bag 랜덤 방식: 7종류를 섞어서 순서대로 뽑고, 다 쓰면 다시 섞음"""
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn_piece(self):
        key = self.get_next_shape_key()
        return Piece(key)

    # ----------------------------------------------------------------
    # 충돌 검사 및 블록 이동 관련 로직
    # ----------------------------------------------------------------
    def valid_position(self, cells):
        """주어진 좌표들이 보드 내에서 유효한 위치인지 검사"""
        for r, c in cells:
            if c < 0 or c >= COLS:
                return False
            if r >= ROWS:
                return False
            if r >= 0 and self.board[r][c] is not None:
                return False
        return True

    def move(self, d_row, d_col):
        piece = self.current
        new_row = piece.row_offset + d_row
        new_col = piece.col_offset + d_col
        new_cells = [(r + new_row, c + new_col) for r, c in piece.cells]

        if self.valid_position(new_cells):
            piece.row_offset = new_row
            piece.col_offset = new_col
            return True
        return False

    def rotate(self):
        piece = self.current
        rotated = piece.rotate_cells()
        new_cells = [(r + piece.row_offset, c + piece.col_offset) for r, c in rotated]

        # 기본 위치에서 회전이 막히면 좌우로 살짝 밀어보는 벽 차기(wall kick) 시도
        kicks = [0, -1, 1, -2, 2]
        for kick in kicks:
            kicked_cells = [(r, c + kick) for r, c in new_cells]
            if self.valid_position(kicked_cells):
                piece.cells = rotated
                piece.col_offset += kick
                return True
        return False

    def hard_drop(self):
        """블록을 더 이상 못 내려갈 때까지 즉시 내리고 고정시킴"""
        while self.move(1, 0):
            self.score += 2  # 하드 드롭 보너스 점수
        self.lock_piece()

    def soft_drop(self):
        """아래 화살표: 한 칸 내리고, 못 내려가면 고정"""
        if self.move(1, 0):
            self.score += 1
        else:
            self.lock_piece()

    def lock_piece(self):
        """현재 블록을 보드에 고정하고 다음 블록 준비"""
        for r, c in self.current.get_cells():
            if r < 0:
                # 블록이 보드 맨 위에서부터 쌓여서 넘치면 게임 오버
                self.game_over = True
                self.sound.play("game_over")
                return
            self.board[r][c] = self.current.color

        self.clear_lines()

        self.current = self.next_piece
        self.next_piece = self.spawn_piece()

        # 새로 생성된 블록이 바로 겹치면 게임 오버
        if not self.valid_position(self.current.get_cells()):
            self.game_over = True
            self.sound.play("game_over")

    def clear_lines(self):
        """가득 찬 줄을 찾아서 삭제하고, 위쪽 줄들을 아래로 내림"""
        full_rows = [r for r in range(ROWS) if all(self.board[r][c] is not None for c in range(COLS))]

        if not full_rows:
            return

        for r in full_rows:
            del self.board[r]
            self.board.insert(0, [None for _ in range(COLS)])

        cleared = len(full_rows)
        self.lines_cleared_total += cleared

        # 점수 계산 (동시 삭제 줄 수가 많을수록 보너스)
        score_table = {1: 100, 2: 300, 3: 500, 4: 800}
        self.score += score_table.get(cleared, 0) * self.level

        prev_level = self.level

        # 10줄마다 레벨업 + 낙하 속도 증가
        self.level = self.lines_cleared_total // 10 + 1
        self.fall_speed = max(100, BASE_FALL_SPEED - (self.level - 1) * 60)

        if self.level > prev_level:
            self.sound.play("level_up")
        else:
            self.sound.play("line_clear")

    # ----------------------------------------------------------------
    # 그리기 관련 함수
    # ----------------------------------------------------------------
    def draw_board(self):
        # 보드 배경
        pygame.draw.rect(self.screen, BLACK, (0, 0, BOARD_WIDTH, BOARD_HEIGHT))

        # 쌓여있는 블록 그리기
        for r in range(ROWS):
            for c in range(COLS):
                color = self.board[r][c]
                if color is not None:
                    self.draw_cell(r, c, color)

        # 격자 그리기
        for r in range(ROWS + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (0, r * CELL_SIZE), (BOARD_WIDTH, r * CELL_SIZE))
        for c in range(COLS + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (c * CELL_SIZE, 0), (c * CELL_SIZE, BOARD_HEIGHT))

    def draw_cell(self, row, col, color, offset_x=0, offset_y=0):
        x = col * CELL_SIZE + offset_x
        y = row * CELL_SIZE + offset_y
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, BLACK, rect, 2)  # 블록 테두리

    def draw_current_piece(self):
        for r, c in self.current.get_cells():
            if r >= 0:
                self.draw_cell(r, c, self.current.color)

    def draw_ghost_piece(self):
        """블록이 떨어질 위치를 미리 보여주는 반투명 그림자"""
        piece = self.current
        ghost_row_offset = piece.row_offset

        while True:
            test_cells = [(r + 1, c + piece.col_offset) for r, c in piece.cells]
            # row_offset을 하나씩 늘려가며 충돌 검사
            shifted = [(r + (ghost_row_offset - piece.row_offset) + 1, c) for r, c in
                       [(r + piece.row_offset, c + piece.col_offset) for r, c in piece.cells]]
            if self.valid_position(shifted):
                ghost_row_offset += 1
            else:
                break

        ghost_cells = [(r + ghost_row_offset, c + piece.col_offset) for r, c in piece.cells]

        ghost_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        ghost_color = (*piece.color, 80)
        for r, c in ghost_cells:
            if r >= 0:
                ghost_surface.fill(ghost_color)
                self.screen.blit(ghost_surface, (c * CELL_SIZE, r * CELL_SIZE))

    def draw_side_panel(self):
        panel_x = BOARD_WIDTH
        pygame.draw.rect(self.screen, (25, 25, 35), (panel_x, 0, SIDE_PANEL_WIDTH, SCREEN_HEIGHT))

        # 점수 및 레벨 표시
        score_text = self.font_small.render(f"점수: {self.score}", True, WHITE)
        level_text = self.font_small.render(f"레벨: {self.level}", True, WHITE)
        lines_text = self.font_small.render(f"삭제 줄: {self.lines_cleared_total}", True, WHITE)

        self.screen.blit(score_text, (panel_x + 20, 30))
        self.screen.blit(level_text, (panel_x + 20, 70))
        self.screen.blit(lines_text, (panel_x + 20, 110))

        # 다음 블록 미리보기
        next_label = self.font_small.render("다음 블록", True, WHITE)
        self.screen.blit(next_label, (panel_x + 20, 170))

        preview_origin_x = panel_x + 40
        preview_origin_y = 210
        for r, c in self.next_piece.cells:
            rect = pygame.Rect(
                preview_origin_x + c * CELL_SIZE,
                preview_origin_y + r * CELL_SIZE,
                CELL_SIZE, CELL_SIZE
            )
            pygame.draw.rect(self.screen, self.next_piece.color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 2)

        # 조작법 안내
        controls = [
            "조작법",
            "← → : 이동",
            "↑ : 회전",
            "↓ : 소프트 드롭",
            "SPACE : 하드 드롭",
            "ESC : 종료",
        ]
        for i, line in enumerate(controls):
            color = WHITE if i == 0 else GRAY
            text = self.font_small.render(line, True, color)
            self.screen.blit(text, (panel_x + 20, 350 + i * 30))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        text = self.font_big.render("GAME OVER", True, (240, 60, 60))
        restart_text = self.font_small.render("R 키를 눌러 다시 시작", True, WHITE)

        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))

        self.screen.blit(text, text_rect)
        self.screen.blit(restart_text, restart_rect)

    # ----------------------------------------------------------------
    # 메인 루프
    # ----------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

                    if self.game_over:
                        if event.key == pygame.K_r:
                            self.reset_game()
                        continue

                    if event.key == pygame.K_LEFT:
                        if self.move(0, -1):
                            self.sound.play("move")
                    elif event.key == pygame.K_RIGHT:
                        if self.move(0, 1):
                            self.sound.play("move")
                    elif event.key == pygame.K_UP:
                        if self.rotate():
                            self.sound.play("rotate")
                    elif event.key == pygame.K_DOWN:
                        self.soft_drop()
                    elif event.key == pygame.K_SPACE:
                        self.sound.play("drop")
                        self.hard_drop()

            if not self.game_over:
                # 자동 낙하 처리
                self.fall_time += dt
                if self.fall_time >= self.fall_speed:
                    self.fall_time = 0
                    if not self.move(1, 0):
                        self.lock_piece()

            # 화면 그리기
            self.screen.fill(BLACK)
            self.draw_board()

            if not self.game_over:
                self.draw_ghost_piece()
                self.draw_current_piece()

            self.draw_side_panel()

            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()


if __name__ == "__main__":
    game = Tetris()
    game.run()