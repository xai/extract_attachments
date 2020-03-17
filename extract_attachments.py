#!/usr/bin/env python3
#
# Copyright (C) 2020 Olaf Lessenich
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License v2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 021110-1307, USA.

import argparse
import multiprocessing
import os
from multiprocessing import Process, Value, Lock, Queue
from queue import Empty
from time import perf_counter
import re

import mailbox


class Counter(object):

    def __init__(self, lock, attachments=0, messages=0, mboxes=0):
        self.lock = lock
        self.attachments = Value('i', attachments)
        self.messages = Value('i', messages)
        self.mboxes = Value('i', mboxes)

    def add_attachment(self, attachments):
        with self.lock:
            self.attachments.value += attachments

    def add_messages(self, messages):
        with self.lock:
            self.messages.value += messages

    def add_mboxes(self, mboxes):
        with self.lock:
            self.mboxes.value += mboxes

    def get_attachments(self):
        with self.lock:
            return self.attachments.value

    def get_messages(self):
        with self.lock:
            return self.messages.value

    def get_mboxes(self):
        with self.lock:
            return self.mboxes.value


verbose = False


def print_usage(path):
    print("Usage: %s [MAILDIR]" % path)


def extract_attachment(key, message, directory, pattern, counter, dry_run):
    for part in message.walk():
        if part.get_content_maintype() == 'multipart' \
           or part.get_content_maintype() == 'text' \
           or part.get('Content-Disposition') == 'inline' \
           or part.get('Content-Disposition') is None:
            continue

        filename = part.get_filename()

        if re.search(re.compile(pattern), filename):
            counter.add_attachment(1)
            destination = os.path.join(directory, key)
            print(filename)

            if not dry_run:
                if not os.path.exists(destination):
                    os.makedirs(destination)
                fp = open(os.path.join(destination, filename), 'wb')
                fp.write(part.get_payload(decode=True))
                fp.close()


def run(mbox, counter, dry_run, directory, pattern):
    counter.add_mboxes(1)

    for key, message in mbox.iteritems():
        message_id = message['Message-Id']
        if message_id is None:
            print("No Message-Id found")
            continue

        counter.add_messages(1)
        extract_attachment(key, message, directory, pattern, counter, dry_run)

    for subdir in mbox.list_folders():
        print("Subdir found: %s", subdir)
        run(subdir, counter, dry_run, directory, pattern)


def process(queue, counter, dry_run, directory, pattern):
    if verbose:
        print("Started process %d" % os.getpid())

    while not queue.empty():
        try:
            target_dir = queue.get(False)
            run(mailbox.Maildir(target_dir), counter, dry_run, directory,
                pattern)
        except Empty:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n",
                        "--dry-run",
                        help="perform a trial run with no changes made",
                        action="store_true")
    parser.add_argument("-p",
                        "--pattern",
                        help="regex pattern that filename must match",
                        type=str,
                        default=".*")
    parser.add_argument("-d",
                        "--directory",
                        help="where to save attachments",
                        type=str,
                        default="attachments")
    parser.add_argument("-v",
                        "--verbose",
                        help="show verbose output",
                        action="store_true")
    parser.add_argument("target_dirs", default=[], nargs="+")
    args = parser.parse_args()

    verbose = args.verbose

    counter = Counter(Lock())
    num_cores = multiprocessing.cpu_count()

    queue = Queue()
    for target_dir in args.target_dirs:
        if os.path.isdir(target_dir):
            queue.put(target_dir)

    procs = []
    for i in range(num_cores):
        procs.append(Process(target=process,
                             args=(queue, counter, args.dry_run,
                                   args.directory, args.pattern)))

    start_time = perf_counter()

    for p in procs:
        p.start()

    for p in procs:
        p.join()

    if verbose:
        elapsed_time = perf_counter() - start_time
        elapsed_min = elapsed_time / 60
        elapsed_sec = elapsed_time % 60
        print()
        print("Processed %d mailboxes with %d mails." %
              (counter.get_mboxes(), counter.get_messages()))
        print("Extracted %d attachments." % counter.get_attachments())
        print("Finished after %dm %ds." % (elapsed_min, elapsed_sec))
