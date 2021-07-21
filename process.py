import subprocess
import threading
import os, signal

from time import sleep

PIPE = subprocess.PIPE

class TaskQueue:
    def __init__(self):
        self.queue = []
        self.in_progress_tasks = []
        self.on_hold = 0

    def __bool__(self):
        return bool(self.queue)


tasks = TaskQueue()


def popen_and_call(popen_args, popen_kwargs, on_exit, task):
    """Runs the given args in a subprocess.Popen, and then calls the function
    on_exit when the subprocess completes. on_exit is a callable object,
    popen_args is a list/tuple of args that would give to subprocess.Popen
    and popen_kwargs is a dict of args that would give to subprocess.Popen.

    Courtesy: https://stackoverflow.com/a/2581943/12118546
    """
    def run_in_thread(on_exit, popen_args, popen_kwargs, task):
        proc = subprocess.Popen(*popen_args, **popen_kwargs)
        task.pid = proc.pid
        proc.wait()
        on_exit()
        return
    thread = threading.Thread(target=run_in_thread, args=(on_exit, popen_args, popen_kwargs, task))
    thread.start()
    # returns immediately after the thread starts
    return thread


class Task:
    def __init__(self, cmd, priority):
        self.cmd = cmd
        self.priority = priority
        self.pid = None
        tasks.queue.append(self)
        tasks.queue.sort(key=lambda task: -task.priority)

    def on_done(self):
        tasks.in_progress_tasks.remove(self)

    def start(self):
        if self.pid:
            os.kill(self.pid, signal.SIGCONT)
            tasks.on_hold -= 1
        else:
            kwargs = {
                #"stdout": PIPE, "stderr": PIPE,
                "shell": True,
            }
            self.pid = popen_and_call([self.cmd], kwargs, self.on_done, self)

        tasks.in_progress_tasks.append(self)
        tasks.in_progress_tasks.sort(key=lambda task: task.priority)

        tasks.queue.remove(self)

    def pause(self):
        if self.pid:
            os.kill(self.pid, signal.SIGSTOP)
            tasks.in_progress_tasks.remove(self)
            tasks.queue.append(self)
            tasks.queue.sort(key=lambda task: -task.priority)
            tasks.on_hold += 1



    def __repr__(self):
        #return f"{self.cmd=} {self.priority=} {self.pid=}"
        return f"[{self.priority}]"

MAXIMUM_CONCURRENT_TASKS = 2
MAXIMUM_ON_HOLD_TASKS = 2

if __name__ == "__main__":
    Task("sleep 5 && echo Hi0", 0)
    Task("sleep 5 && echo Hi10", 10)
    Task("sleep 5 && echo Hi2", 2)

    i = 0

    while True:
        print(i)
        print("QUEUE: ", tasks.queue)
        print("IN_PROGRESS: ", tasks.in_progress_tasks)
        print("ON_HOLD: ", tasks.on_hold)

        busy = len(tasks.in_progress_tasks) >= MAXIMUM_CONCURRENT_TASKS

        if not busy and tasks:
            tasks.queue[0].start()
        elif busy and tasks and tasks.on_hold < MAXIMUM_ON_HOLD_TASKS:
            top_priority_queued_task  = tasks.queue[0]
            lowest_priority_in_progress_task = tasks.in_progress_tasks[0]
            if top_priority_queued_task.priority > lowest_priority_in_progress_task.priority:
                lowest_priority_in_progress_task.pause()
                top_priority_queued_task.start()

        if (i == 3):
            Task("sleep 5 && echo Hi100", 100)
            Task("sleep 5 && echo Hi101", 101)
            Task("sleep 5 && echo Hi102", 102)

        i += 1
        sleep(0.1)
