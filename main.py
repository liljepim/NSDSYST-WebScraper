from multiprocessing import Lock, Manager, Process

from async_client import WorkerNode


def main():
    manager = Manager()
    email_list = manager.list()
    visited_list = manager.list()
    link_queue = manager.Queue()
    email_lock = Lock()
    visit_lock = Lock()

    # Initial DLSU link here
    link_queue.put("https://www.dlsu.edu.ph")

    processes = []
    for _ in range(4):
        worker = WorkerNode(
            email_list, visited_list, link_queue, email_lock, visit_lock
        )
        p = Process(target=worker.start)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("\nCollected Emails:")
    for email in email_list:
        print(email)


if __name__ == "__main__":
    main()
