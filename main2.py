import argparse
import json
import pickle
import os

import numpy as np
import pandas as pd
import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 1200, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("OS Scheduler Simulator")

font = pygame.font.SysFont("consolas", 22)
small_font = pygame.font.SysFont("consolas", 16)
clock = pygame.time.Clock()

MODEL_PATH = os.path.join(os.path.dirname(__file__), "scheduler_model.pkl")
model_loaded = False
pipeline = None
le = None

try:
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    pipeline = model_data["pipeline"]
    le = model_data["label_encoder"]
    model_loaded = True
    print("✅ Loaded ML model from scheduler_model.pkl")
except Exception as e:
    print(f"⚠️ Could not load ML model: {e}")
    model_loaded = False

PROCESS_COLORS = [
    (99,102,241),(236,72,153),(16,185,129),
    (245,158,11),(59,130,246),(139,92,246)
]


def load_state_file(file_path):
    global color_index, prediction_ready, running_sim, current_algo, prediction_reason, state_mode

    if not os.path.exists(file_path):
        print(f"⚠️ State file not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        state = json.load(f)

    for p in state.get('processes', []):
        ptype = 'IO' if p.get('process_type') == 'IO-bound' else 'CPU'
        processes.append(Process(
            p.get('id', 'P?'),
            int(p.get('arrival_time', 0)),
            int(p.get('burst_time', 0)),
            int(p.get('priority', 1)),
            ptype,
            PROCESS_COLORS[color_index % len(PROCESS_COLORS)]
        ))
        color_index += 1

    current_algo = state.get('algorithm', current_algo)
    prediction_reason = state.get('reason', f"Loaded predicted algorithm: {current_algo}")
    prediction_ready = True
    state_mode = True
    running_sim = True


def make_queue_stats(processes):
    num_processes = len(processes)
    burst_times = [p.burst for p in processes]
    arrival_times = [p.arrival for p in processes]
    priorities = [p.priority for p in processes]
    io_count = sum(1 for p in processes if p.ptype == "IO")
    pct_io_bound = io_count / num_processes

    return {
        "num_processes": num_processes,
        "mean_burst": float(np.mean(burst_times)),
        "std_burst": float(np.std(burst_times)),
        "max_burst": float(np.max(burst_times)),
        "min_burst": float(np.min(burst_times)),
        "arrival_spread": float(np.max(arrival_times) - np.min(arrival_times)),
        "mean_priority": float(np.mean(priorities)),
        "priority_var": float(np.var(priorities)),
        "pct_io_bound": float(pct_io_bound),
        "pct_cpu_bound": float(1.0 - pct_io_bound),
    }


def get_queue_reason(stats, algo):
    if stats["pct_io_bound"] >= 0.5 and algo == "Round Robin":
        return f"High I/O mix ({int(stats['pct_io_bound']*100)}% I/O-bound). Round Robin helps keep the CPU responsive."
    if stats["priority_var"] > 4 and stats["mean_priority"] >= 5 and algo == "Priority":
        return f"High priority variance ({stats['priority_var']:.1f}). Priority scheduling prevents critical jobs from waiting too long."
    if stats["std_burst"] > 5 and algo in ["SJF", "SRTF"]:
        return "Large burst-time variation. Shortest-job scheduling reduces waiting time for short processes."
    return f"Balanced queue statistics. {algo} is a reasonable choice for this workload."


def ml_predict(processes):
    if not processes:
        return "FCFS"

    if model_loaded:
        stats = make_queue_stats(processes)
        input_df = pd.DataFrame([stats])
        pred_idx = pipeline.predict(input_df)[0]
        return le.inverse_transform([pred_idx])[0]

    if len(processes) <= 3:
        return "FCFS"
    avg_bt = sum(p.burst for p in processes) / len(processes)
    if avg_bt > 6:
        return "SJF"
    if any(p.ptype == "IO" for p in processes):
        return "RR"
    return "PRIORITY"

BG = (2, 6, 23)
CARD = (15, 23, 42)
BORDER = (30, 41, 59)
TEXT = (226, 232, 240)

# ─── Process ───
class Process:
    def __init__(self, pid, arrival, burst, priority, ptype, color):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.remaining = burst
        self.priority = priority
        self.ptype = ptype
        self.color = color
        self.x = WIDTH + 100
        self.y = 0
        self.target_x = self.x
        self.target_y = self.y
        self.completion = None

# ─── STATE ───
processes = []
ready = []
cpu = None
done = []

time_elapsed = 0.0
frame = 0

quantum = 2
current_algo = "RR"
prediction_reason = "Click PREDICT to choose a scheduling algorithm."
prediction_ready = False

pid_input = "P1"
at_input = "0"
bt_input = "5"
priority_input = "1"
ptype = "CPU"

active_field = None

running_sim = False
simulation_complete = False
q_timer = 0
speed = 40
state_mode = False

# ─── UI ───
def draw_box(x, y, w, h, label):
    pygame.draw.rect(screen, (0,0,0), (x+5,y+5,w,h), border_radius=12)
    pygame.draw.rect(screen, CARD, (x,y,w,h), border_radius=12)
    pygame.draw.rect(screen, (99,102,241), (x,y,w,h), 2, border_radius=12)
    screen.blit(small_font.render(label, True, (148,163,184)), (x+12,y-18))

def draw_input(x,y,w,h,text,active):
    rect = pygame.Rect(x,y,w,h)
    pygame.draw.rect(screen, CARD, rect, border_radius=6)
    pygame.draw.rect(screen, (99,102,241) if active else BORDER, rect,2)
    screen.blit(small_font.render(text, True, TEXT), (x+5,y+5))
    return rect

def draw_button(x,y,w,h,text,color):
    rect = pygame.Rect(x,y,w,h)
    mouse = pygame.mouse.get_pos()
    hover = rect.collidepoint(mouse)
    c = tuple(min(255, c+30) if hover else c for c in color)
    pygame.draw.rect(screen,c,rect,border_radius=8)
    pygame.draw.rect(screen,(255,255,255),rect,1,border_radius=8)
    screen.blit(small_font.render(text,True,(0,0,0)),(x+10,y+5))
    return rect

def draw_process(p):
    pygame.draw.rect(screen, p.color, (p.x,p.y,80,45), border_radius=10)
    pygame.draw.rect(screen, (255,255,255), (p.x,p.y,80,45), 1, border_radius=10)
    screen.blit(small_font.render(p.pid,True,(255,255,255)),(p.x+10,p.y+5))
    screen.blit(small_font.render(f"P:{p.priority}",True,(255,255,255)),(p.x+10,p.y+22))

def draw_process_at(p, x, y):
    pygame.draw.rect(screen, p.color, (x,y,80,45), border_radius=10)
    pygame.draw.rect(screen, (255,255,255), (x,y,80,45), 1, border_radius=10)
    screen.blit(small_font.render(p.pid,True,(255,255,255)),(x+10,y+5))
    screen.blit(small_font.render(f"P:{p.priority}",True,(255,255,255)),(x+10,y+22))

def move_smooth(p, tx, ty):
    p.x += (tx-p.x)*0.08
    p.y += (ty-p.y)*0.08

def draw_table(scroll_offset):
    x, y = 50, 600
    headers = ["PID","AT","BT","PR","TYPE","CT","TAT","WT"]
    width = 960
    table_top = y + 30
    view_rect = pygame.Rect(x, table_top, width, table_view_height)

    for i,h in enumerate(headers):
        screen.blit(small_font.render(h,True,(99,102,241)),(x+i*120,y))

    screen.set_clip(view_rect)
    for r,p in enumerate(done):
        row_y = table_top + r * table_row_height - scroll_offset
        if row_y + table_row_height < table_top or row_y > table_top + table_view_height:
            continue
        completion = round(p.completion)
        tat = round(p.completion - p.arrival)
        wt = round(tat - p.burst)
        vals = [p.pid,p.arrival,p.burst,p.priority,p.ptype,completion,tat,wt]

        for c,v in enumerate(vals):
            screen.blit(small_font.render(str(v),True,(200,200,200)),
                        (x+c*120,row_y))
    screen.set_clip(None)

    if len(done) * table_row_height > table_view_height:
        track_x = x + width + 10
        track_rect = pygame.Rect(track_x, table_top, 10, table_view_height)
        pygame.draw.rect(screen, BORDER, track_rect, border_radius=5)
        total_height = len(done) * table_row_height
        scroll_max = total_height - table_view_height
        thumb_height = max(24, int(table_view_height * table_view_height / total_height))
        thumb_y = table_top + int(table_scroll * (table_view_height - thumb_height) / max(1, scroll_max))
        pygame.draw.rect(screen, (99,102,241), (track_x, thumb_y, 10, thumb_height), border_radius=5)

# ─── MAIN LOOP ───
running = True
color_index = 0
done_view_width = 520
done_offset = 0
scroll_step = 40

table_view_height = 140
table_scroll = 0
table_row_height = 30

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=str, default=None, help="Path to JSON state file to preload simulation.")
    args = parser.parse_args()
    if args.state:
        load_state_file(args.state)

while running:
    dt = clock.tick(speed) / 1000.0

    # Gradient BG
    for y in range(HEIGHT):
        color = (2, 6 + int(y*0.05), 23 + int(y*0.08))
        pygame.draw.line(screen, color, (0,y), (WIDTH,y))

    draw_box(50,260,350,100,"READY")
    draw_box(450,260,120,100,"CPU")

    # Dynamic DONE box with horizontal scroll
    done_card_width = 80
    done_card_spacing = 90
    if done:
        done_total_width = max(done_view_width, 20 + (len(done) - 1) * done_card_spacing + done_card_width)
    else:
        done_total_width = done_view_width
    done_max_offset = max(0, done_total_width - done_view_width)
    done_offset = min(max(done_offset, 0), done_max_offset)
    draw_box(650,260,done_view_width,100,"DONE")
    done_area = pygame.Rect(650,260,done_view_width,100)
    table_area = pygame.Rect(50, 630, 960, table_view_height)

    scroll_left_rect = None
    scroll_right_rect = None
    scroll_controls_y = 260 + 100 + 10
    if done_total_width > done_view_width:
        scroll_left_x = 650 + done_view_width // 2 - 55
        scroll_right_x = 650 + done_view_width // 2 + 15
        scroll_left_rect = pygame.Rect(scroll_left_x, scroll_controls_y, 40, 36)
        scroll_right_rect = pygame.Rect(scroll_right_x, scroll_controls_y, 40, 36)

    screen.blit(font.render(f"TIME: {int(time_elapsed)}",True,(99,102,241)),(900,40))
    screen.blit(font.render(current_algo,True,(236,72,153)),(520,40))
    if not state_mode:
        screen.blit(small_font.render(prediction_reason,True,(200,200,200)),(50,40))

        # INPUT
        pid_rect = draw_input(50,130,80,30,pid_input,active_field=="pid")
        at_rect  = draw_input(140,130,60,30,at_input,active_field=="at")
        bt_rect  = draw_input(210,130,60,30,bt_input,active_field=="bt")
        pr_rect  = draw_input(280,130,60,30,priority_input,active_field=="pr")

        type_btn = draw_button(350,130,90,30,ptype,(245,158,11))
        add_btn = draw_button(460,130,70,30,"ADD",(16,185,129))
        predict_btn = draw_button(540,130,90,30,"PREDICT",(99,102,241))
        simulate_btn = draw_button(640,130,140,30,"SHOW SIMULATION",(16,185,129))
    else:
        screen.blit(small_font.render(prediction_reason,True,(200,200,200)),(50,70))

    # EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not state_mode:
                if pid_rect.collidepoint(event.pos): active_field="pid"
                elif at_rect.collidepoint(event.pos): active_field="at"
                elif bt_rect.collidepoint(event.pos): active_field="bt"
                elif pr_rect.collidepoint(event.pos): active_field="pr"
                else: active_field=None

                if type_btn.collidepoint(event.pos):
                    ptype = "IO" if ptype == "CPU" else "CPU"

                if add_btn.collidepoint(event.pos):
                    try:
                        processes.append(Process(
                            pid_input,int(at_input),int(bt_input),
                            int(priority_input),ptype,
                            PROCESS_COLORS[color_index%len(PROCESS_COLORS)]
                        ))
                        color_index+=1
                        pid_input=f"P{len(processes)+1}"
                    except:
                        print("Invalid input")

                if predict_btn.collidepoint(event.pos):
                    if processes:
                        current_algo = ml_predict(processes)
                        if model_loaded:
                            stats = make_queue_stats(processes)
                            prediction_reason = get_queue_reason(stats, current_algo)
                        else:
                            prediction_reason = "ML model missing: using fallback heuristic prediction."
                        prediction_ready = True
                    else:
                        prediction_reason = "Add at least one process before predicting."
                        prediction_ready = False

                if simulate_btn.collidepoint(event.pos):
                    if not processes and not ready and cpu is None:
                        prediction_reason = "Add processes before showing the simulation."
                    elif not prediction_ready:
                        current_algo = ml_predict(processes)
                        if model_loaded and processes:
                            stats = make_queue_stats(processes)
                            prediction_reason = get_queue_reason(stats, current_algo)
                        elif not model_loaded:
                            prediction_reason = "ML model missing: using fallback heuristic prediction."
                        else:
                            prediction_reason = "No processes available to predict."
                        prediction_ready = bool(processes)
                        running_sim = bool(processes)
                    else:
                        running_sim = True

            if scroll_left_rect and scroll_left_rect.collidepoint(event.pos):
                done_offset = max(0, done_offset - scroll_step)
            if scroll_right_rect and scroll_right_rect.collidepoint(event.pos):
                done_offset = min(done_offset + scroll_step, done_max_offset)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if done_area.collidepoint(event.pos):
                if event.button == 4:
                    done_offset = max(0, done_offset - scroll_step)
                else:
                    done_offset = min(done_offset + scroll_step, done_max_offset)

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if done_area.collidepoint(mouse_pos):
                if event.y > 0:
                    done_offset = max(0, done_offset - scroll_step)
                elif event.y < 0:
                    done_offset = min(done_offset + scroll_step, max(0, done_total_width - done_view_width))
            elif table_area.collidepoint(mouse_pos):
                max_table_scroll = max(0, len(done) * table_row_height - table_view_height)
                if event.y > 0:
                    table_scroll = max(0, table_scroll - scroll_step)
                elif event.y < 0:
                    table_scroll = min(table_scroll + scroll_step, max_table_scroll)

        if not state_mode and event.type == pygame.KEYDOWN and active_field:
            if event.key == pygame.K_BACKSPACE:
                if active_field=="pid": pid_input=pid_input[:-1]
                elif active_field=="at": at_input=at_input[:-1]
                elif active_field=="bt": bt_input=bt_input[:-1]
                elif active_field=="pr": priority_input=priority_input[:-1]
            else:
                if active_field=="pid":
                    pid_input+=event.unicode
                elif active_field in ["at","bt","pr"] and event.unicode.isdigit():
                    if active_field=="at": at_input+=event.unicode
                    elif active_field=="bt": bt_input+=event.unicode
                    elif active_field=="pr": priority_input+=event.unicode

    # ─── SIMULATION ───
    if running_sim:

        for p in processes[:]:
            if p.arrival <= time_elapsed:
                ready.append(p)
                processes.remove(p)

        if current_algo == "FCFS":
            if cpu is None and ready:
                cpu = ready.pop(0)
            if cpu:
                cpu.remaining -= dt
                if cpu.remaining <= 0:
                    cpu.completion = time_elapsed + dt
                    index = len(done)
                    cpu.target_x = 670 + index * 90
                    cpu.target_y = 280
                    done.append(cpu)
                    cpu = None

        elif current_algo == "SJF":
            if cpu is None and ready:
                ready.sort(key=lambda x:x.burst)
                cpu = ready.pop(0)
            if cpu:
                cpu.remaining -= dt
                if cpu.remaining <= 0:
                    cpu.completion = time_elapsed + dt
                    index = len(done)
                    cpu.target_x = 670 + index * 90
                    cpu.target_y = 280
                    done.append(cpu)
                    cpu = None

        elif current_algo == "PRIORITY":
            if cpu is None and ready:
                ready.sort(key=lambda x:-x.priority)
                cpu = ready.pop(0)
            if cpu:
                cpu.remaining -= dt
                if cpu.remaining <= 0:
                    cpu.completion = time_elapsed + dt
                    index = len(done)
                    cpu.target_x = 670 + index * 90
                    cpu.target_y = 280
                    done.append(cpu)
                    cpu = None

        elif current_algo == "RR":
            if cpu is None and ready:
                cpu = ready.pop(0)
                q_timer = 0
            if cpu:
                cpu.remaining -= dt
                q_timer += dt
                if cpu.remaining <= 0:
                    cpu.completion = time_elapsed + dt
                    index = len(done)
                    cpu.target_x = 670 + index * 90
                    cpu.target_y = 280
                    done.append(cpu)
                    cpu = None
                elif q_timer >= quantum:
                    ready.append(cpu)
                    cpu = None

        if not processes and not ready and cpu is None:
            running_sim = False
            simulation_complete = True

    # DRAW
    for i,p in enumerate(ready):
        move_smooth(p,70+i*90,280)
        draw_process(p)

    if cpu:
        pygame.draw.rect(screen,cpu.color,(460,270,100,60),border_radius=12)
        move_smooth(cpu,470,280)
        draw_process(cpu)

    if done:
        clip_rect = pygame.Rect(650,260,done_view_width,100)
        screen.set_clip(clip_rect)
        for p in done:
            move_smooth(p, p.target_x, p.target_y)
            draw_process_at(p, p.x - done_offset, p.y)
        screen.set_clip(None)

        if scroll_left_rect:
            track_rect = pygame.Rect(650, 360, done_view_width, 8)
            pygame.draw.rect(screen, BORDER, track_rect, border_radius=4)
            thumb_width = max(40, int(done_view_width * done_view_width / done_total_width))
            thumb_x = 650 + int(done_offset * (done_view_width - thumb_width) / max(1, done_total_width - done_view_width))
            pygame.draw.rect(screen, (99,102,241), (thumb_x, 362, thumb_width, 8), border_radius=4)
            draw_button(scroll_left_rect.x, scroll_left_rect.y, scroll_left_rect.w, scroll_left_rect.h, "<", (99,102,241))
        if scroll_right_rect:
            draw_button(scroll_right_rect.x, scroll_right_rect.y, scroll_right_rect.w, scroll_right_rect.h, ">", (99,102,241))

        draw_table(table_scroll)

    if simulation_complete and done:
        screen.blit(font.render("SIMULATION COMPLETE",True,(16,185,129)),(400,420))
        screen.blit(font.render("Close the window to exit.", True, (148,163,184)), (400,450))

    pygame.display.update()

    if running_sim:
        time_elapsed += dt

pygame.quit()
sys.exit()
