#!/usr/bin/env python
# Submit and maintain a big batch of jobs based on book file
# State:
# " ": not submitted
# "r": running
# "c": completed - was running, dissapeared from job queue, pK.out generated
# "e": error - was running, dissapeared from job queue and no pK.out

import os
import subprocess
import getpass


n_active = 10   # number of active jobs to maintain
queue_book = "book.txt"

# has to be interactive:
job_name = "run.sh"


class ENTRY:
    def __init__(self):
        self.name = ""
        self.state = " "

    def __str__(self):
        return f"{self.name:6s} {self.state:1s}"


def read_book(book):
    entries = []
    lines = open(book).readlines()
    for line in lines:
        rawtxt = line.strip().split("#")[0]
        fields = rawtxt.split()
        entry = ENTRY()
        entry.name = fields[0]
        if len(fields) > 1:
            entry.state = fields[1].lower()
        entries.append(entry)

    return entries


def get_jobs(job_name):
    """
    (base) cat:~/projects$ ps -u
    USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
    cat          9  0.0  0.0   9540  5568 pts/0    Ss   15:20   0:00 -bash
    cat        116  0.0  0.0   9552  5652 pts/1    Ss   15:50   0:01 -bash
    cat        569  0.5  1.3 435456 133116 pts/1   Sl+  17:28   0:09 ~/miniconda3/bin/python3.11 ~/miniconda3/bin/jupyter-lab
    cat        981  0.0  0.0  10460  3252 pts/0    R+   17:57   0:00 ps -u

    (base) cat:~/projects$ pgrep bash
    9
    116
    """
    #pgrep_cmd = f"pgrep {job_name}"
    #poc_id = subprocess.Popen([pgrep_cmd]], stdout=subprocess.PIPE).stdout.readlines()

    lines = subprocess.Popen(["ps", "-u", f"{getpass.getuser()}"], stdout=subprocess.PIPE).stdout.readlines()
    job_uids = [x.decode("ascii").split()[0] for x in lines if x.decode("ascii").find(job_name) > 0]
    job_uids = [x for x in job_uids if x and x != "PID"]

    jobs = []
    for uid in job_uids:
        output = subprocess.Popen(["pwdx", uid], stdout=subprocess.PIPE).stdout.readlines()[0].decode("ascii")
        job = output.split(":")[1].split("/")[-1].strip()
        if job:
            jobs.append(job)
    return jobs


def get_jobs0():
    lines = subprocess.Popen(["ps", "-u", f"{getpass.getuser()}"], stdout=subprocess.PIPE).stdout.readlines()
    job_uids = [x.decode("ascii").split()[0] for x in lines if x.decode("ascii").find(job_name) > 0]
    job_uids = [x for x in job_uids if x and x != "PID"]

    jobs = []
    for uid in job_uids:
        output = subprocess.Popen(["pwdx", uid], stdout=subprocess.PIPE).stdout.readlines()[0].decode("ascii")
        job = output.split(":")[1].split("/")[-1].strip()
        if job:
            jobs.append(job)
    return jobs


def main():
    entries = read_book(queue_book)
    jobs = get_jobs()
    n_jobs = len(jobs)

    new_entries = []
    for entry in entries:
        if entry.state == " ":
            n_jobs += 1
            if n_jobs <= n_active:
                os.chdir(entry.name)
                subprocess.Popen("../%s" % job_name, close_fds=True, stdout=open("run.log", "w"))
                os.chdir("../")
                entry.state = "r"
        elif entry.state == "r":
            if entry.name not in jobs:   # running to not running anymore
                if os.path.isfile("%s/pK.out" % entry.name):
                    entry.state = "c"
                else:
                    entry.state = "e"

        new_entries.append(entry)

    newlines = [f"{e}\n" for e in new_entries]
    open(queue_book, "w").writelines(newlines)


if __name__ == "__main__":
    main()
