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


n_active = 10   # keep this number of active jobs
queue_book = "book"
job_name = "run.sh"
#job_name = "run_dummy.sh"


class ENTRY:
    def __init__(self):
        self.name = ""
        self.state = " "

    def printme(self):
        return "%-6s %c" % (self.name, self.state)


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


def get_jobs():
    lines = subprocess.Popen(["ps", "-u", "%s" % getpass.getuser()], stdout=subprocess.PIPE).stdout.readlines()

    #job_name = "pycharm"
    job_uids = [x.decode("ascii").split()[0] for x in lines if x.decode("ascii").find(job_name) > 0]
    job_uids = [x for x in job_uids if x and x != "PID"]

    jobs = []
    for uid in job_uids:
        output = subprocess.Popen(["pwdx", uid], stdout=subprocess.PIPE).stdout.readlines()[0].decode("ascii")
        job = output.split(":")[1].split("/")[-1].strip()
        if job:
            jobs.append(job)
    return jobs


if __name__ == "__main__":

    entries = read_book(queue_book)

    jobs = get_jobs()
    n_jobs = len(jobs)

    new_entries = []
    for entry in entries:
       
        if entry.state == " ":
            n_jobs += 1
            if n_jobs <= n_active:
                #print(os.getcwd(), entry.name)
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

    newlines = [e.printme()+"\n" for e in new_entries]
    open(queue_book, "w").writelines(newlines)
