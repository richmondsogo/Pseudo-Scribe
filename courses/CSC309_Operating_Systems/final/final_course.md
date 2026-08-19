# Chapter 2: Process Management


\begin{verbatim}
    New ----> Ready
                |
                v
    Running <---- Ready (preempted)
        |         ^
        v         |
    Waiting ----> Ready (event occurs)
        |
        v
    Terminated
\end{verbatim}

\begin{tabularx}{\textwidth}{@{} l X X X @{}}
\toprule
Algorithm & Preemptive? & Advantages & Disadvantages \\
\midrule
FCFS & No & Simple, fair & Convoy effect \\
SJF & Optional & Minimizes average waiting time & Requires burst time prediction \\
SRTF & Yes & Optimal for minimizing waiting time & Overhead of preemption & Real-time systems \\
RR & Yes & Responsive, fair & Context switch overhead \\
Priority & Optional & Supports importance & Starvation, inversion \\
\bottomrule
\end{tabularx}

\begin{verbatim}
Time: 0    4    8    12   16   20   24   26
P1:   |----| |----| |--|
P2:      |----| |---|
P3:         |----| |----|
\end{verbatim}

Average turnaround = (10 + 15 + 23) / 3 = 16.

\subsubsection{Shortest Job First (SJF)}
Selects the process with the smallest burst time. Can be preemptive or non-preemptive.

Example: same processes, non-preemptive SJF order: P2 (5), P3 (8), P1 (10).

\begin{verbatim}
P2: |-----| (5)
P3:       |--------| (8)
P1:                |---------| (10)
\end{verbatim}

Average turnaround = (5 + 13 + 23) / 3 = 13.67.

\subsubsection{Shortest Remaining Time First (SRTF)}
Preemptive version of SJF; if a new process arrives with shorter remaining time, it preempts the current process.

\subsubsection{Round Robin (RR)}
Each process gets a small unit of time (time quantum) and then yields the CPU. Preemptive.

Example: processes with burst times 10, 5, 8, quantum = 4.

\begin{verbatim}
Time: 0    4    8    12   16   20   24   26
P1:   |----| |----| |--|
P2:      |----| |---|
P3:         |----| |----|
\end{verbatim}

Average turnaround depends on quantum.

\subsubsection{Priority Scheduling}
Each process has a priority; higher priority runs first. Can be preemptive or non-preemptive. Starvation is a problem; solved by aging.

\begin{tabularx}{\textwidth}{@{} l X X X X @{}}
\toprule
Algorithm & Preemptive? & Advantages & Disadvantages & Suitable For \\
\midrule
FCFS & No & Simple, fair & Convoy effect & Batch systems \\
SJF & Optional & Minimizes average waiting time & Requires burst time prediction & Batch systems \\
SRTF & Yes & Optimal for minimizing waiting time & Overhead of preemption & Real-time systems \\
RR & Yes & Responsive, fair & Context switch overhead & Time-sharing systems \\
Priority & Optional & Supports importance & Starvation, inversion & Real-time systems \\
\bottomrule
\end{tabularx}

\subsection{Context Switch}
A context switch is the mechanism of saving the state of the current process and restoring the state of the next process. It involves updating PCBs, flushing TLBs, and may involve kernel overhead. Frequent context switches can reduce CPU utilization.

\section{Process Synchronization}

\subsection{Critical Section Problem}
When multiple processes access shared data, the outcome may depend on the order of access, leading to race conditions. The code segment that accesses shared data is called the critical section. A solution must ensure mutual exclusion: only one process can be in its critical section at a time.

Requirements:
\begin{itemize}
\item \textbf{Mutual exclusion}: only one process in critical section.
\item \textbf{Progress}: if no process is in critical section, a process that wants to enter must be allowed.
\item \textbf{Bounded waiting}: a process must eventually be allowed to enter.
\end{itemize}

\subsection{Mutual Exclusion}
Hardware support: test-and-set instruction, swap instruction.

Software solutions: Peterson's algorithm for two processes, Dekker's algorithm.

\subsubsection{Mutex}
A mutex (mutual exclusion lock) is a simple synchronization primitive. Operations: lock() and unlock(). Only one thread can hold the lock.

Example:
\begin{verbatim}
// Thread 1
mutex.lock();
// critical section
mutex.unlock();

// Thread 2
mutex.lock();
// critical section
mutex.unlock();
\end{verbatim}

\subsection{Semaphores}
A semaphore is an integer variable with two atomic operations: wait() (or P) and signal() (or V). A binary semaphore acts like a mutex; a counting semaphore allows multiple instances.

Definition: A semaphore S is a non-negative integer. wait() decrements S; if S becomes negative, the process blocks. signal() increments S; if S was negative, it wakes a blocked process.

Example: controlling access to a pool of resources.

\begin{verbatim}
semaphore mutex = 1; // binary semaphore
semaphore empty = N; // number of empty slots
semaphore full = 0;  // number of full slots

// Producer
wait(empty);
produce();
wait(mutex);
add to buffer;
signal(mutex);
signal(full);

// Consumer
wait(full);
wait(mutex);
remove from buffer;
signal(mutex);
signal(empty);
consume();
\end{verbatim}

\subsection{Monitors}
A monitor is a high-level synchronization construct that encapsulates shared data and the operations that access it. Only one process can be active in a monitor at a time. Condition variables allow waiting for specific events.

Example: a monitor for a bounded buffer.

\begin{verbatim}
monitor BoundedBuffer {
    int buffer[N];
    int count = 0;
    int in = 0, out = 0;
    condition notFull, notEmpty;

    void put(int item) {
        if (count == N) wait(notFull);
        buffer[in] = item;
        in = (in + 1) % N;
        count++;
        signal(notEmpty);
    }

    int get() {
        if (count == 0) wait(notEmpty);
        int item = buffer[out];
        out = (out + 1) % N;
        count--;
        signal(notFull);
        return item;
    }
}
\end{verbatim}

\subsection{Deadlock}
Deadlock occurs when processes are waiting for resources held by each other. Prevention, avoidance, and recovery strategies are discussed in later chapters.

Process management provides the foundation for concurrent execution in modern Operating Systems. The concepts of processes and threads, the algorithms for CPU Scheduling, and the mechanisms for synchronization are essential for building reliable and efficient software. The next chapter will examine Memory Management, including techniques such as Virtual Memory.

\section*{Tutorial Questions}
\begin{enumerate}
\item Define a process and explain the difference between a process and a program.
\item Draw and explain the state transition diagram of a process.
\item Compare user-level threads and kernel-level threads. Provide one advantage and one disadvantage of each.
\item Consider three processes with burst times 8, 4, 9 arriving at time 0. Compute the average waiting time and average turnaround time for FCFS, SJF (non-preemptive), and RR (quantum = 3).
\item Explain the critical section problem and state the three requirements of a solution.
\item Describe how a binary semaphore can be used to implement mutual exclusion. Write pseudocode for two processes that use a semaphore to protect a critical section.
\item What is a monitor? How does it differ from a semaphore?
\item Suppose two processes share a single resource and use a test-and-set instruction for mutual exclusion. Explain why this approach may lead to busy waiting.
\end{enumerate}



# Chapter 3: Memory Management


\section{Memory Management}

Memory management is the core responsibility of an operating system that involves allocating, tracking, and reclaiming main memory for processes. This chapter introduces the concepts of virtual memory and the mechanisms that support it.

The abstraction of virtual memory allows each process to view the available memory as a contiguous address space, independent of the physical RAM installed in the machine. The operating system maintains data structures that translate virtual addresses used by programs into physical addresses in RAM or, when necessary, into secondary storage.

\subsection{Virtual Memory Concepts}
Virtual memory provides isolation and protection between processes while extending the address space beyond the limits of physical memory. It enables features such as memory‑mapped files and on‑demand loading of code and data.

\subsection{Paging Mechanism}
Paging divides both virtual and physical memory into fixed‑size blocks called pages and frames respectively. The operating system uses a page table to keep track of the mapping between a process’s pages and the available frames.

\begin{verbatim}
+-------------------+      +-------------------+
|   Process A       |      |   Physical Memory |
| Code | Data |Heap |      | Frame 0 | Frame 1 |
+-------------------+      +-------------------+
|   Process B       |      | Frame 2 | Frame 3 |
+-------------------+      +-------------------+
|   Free Frames     |      |      ...          |
+-------------------+
\end{verbatim}

\subsection{Page Fault Handling}
When a process accesses a page that is not resident in physical memory, a page fault occurs. The operating system handles the fault by allocating a frame, reading the required page from disk, updating the page table, and restarting the interrupted instruction.

\begin{verbatim}
   +-------------------+    Page Fault    +-------------------+
   |  CPU accesses     |  -------------->|  Page Table Lookup|
   |  memory address   |                 |  (not present)    |
   +-------------------+                 +-------------------+
                                                |
                                                v
                                        +-------------------+
                                        |  Page Fault       |
                                        |  Exception        |
                                        +-------------------+
                                                |
                                                v
                                        +-------------------+
                                        |  Page Fault       |
                                        |  Handler          |
                                        +-------------------+
                                1. Find free frame / evict
                                2. Load page from disk
                                3. Update page table
                                4. Restart faulting instruction
\end{verbatim}

\subsection{Comparison of Physical and Virtual Memory}
\begin{table}[htbp]
\centering
\begin{tabular}{ll}
\toprule
Aspect & Description \\
\midrule
Physical Memory & The actual RAM installed in the computer; limited in size and directly accessible by the CPU. \\
Virtual Memory & An abstraction that provides each process with an address space larger than physical memory, using disk as an extension. \\
\bottomrule
\end{tabular}
\caption{Comparison of Physical and Virtual Memory}
\end{table}

\subsection{Swap Space}
Swap space is a designated area on secondary storage that the operating system uses to store pages that are not currently in physical memory. It allows the system to overcommit memory and to free frames for other processes.

\subsection{Summary}
Memory management combines allocation strategies, protection mechanisms, and swapping policies to present a coherent virtual address space to processes. The next chapter will explore how files are organized and accessed through the file system and I/O subsystem.

\section*{Tutorial Questions}
\begin{enumerate}
\item Explain the difference between physical memory and virtual memory. Provide one advantage of using virtual memory for process isolation.
\item Describe how a page table maps virtual pages to physical frames. Include a brief example with two processes.
\item What is a page fault and what steps does the operating system take to resolve it?
\item Compare the concepts of a frame and a page. Why must they be of the same size?
\item Discuss the purpose of swap space. How does it affect system performance?
\item A process attempts to access a page that is not in memory, causing a page fault. Explain the sequence of events that follow, from detection to resumption of the process.
\item Identify two scenarios where demand paging improves overall system throughput.
\item Outline the conditions under which a page replacement algorithm must be invoked.
\end{enumerate}



# Chapter 4: File Systems and I/O


[TERMINOLOGY]
{
  "File": {
    "preferred_term": "File",
    "definition": "A named collection of related data stored on secondary storage, identified by a pathname, and accessed via I/O operations.",
    "definition_status": "defined",
    "introduced_in": null
  },
  "Directory": {
    "preferred_term": "Directory",
    "definition": "A special file that contains a set of file names and their associated metadata, used to organize files hierarchically.",
    "definition_status": "defined",
    "introduced_in": null
  },
  "Block": {
    "preferred_term": "Block",
    "definition": "A fixed-size unit of data storage, typically 512 bytes or 4096 bytes, that forms the basic building block of a file system.",
    "definition_status": "defined",
    "introduced_in": null
  },
  "Inode": {
    "preferred_term": "Inode",
    "definition": "A data structure in a file system that stores metadata about a file, such as its size, permissions, and pointers to its data blocks.",
    "definition_status": "defined",
    "introduced_in": null
  },
  "Device Driver": {
    "preferred_term": "Device Driver",
    "definition": "A software component that controls a hardware device, providing a standardized interface to the operating system and applications.",
    "definition_status": "defined",
    "introduced_in": null
  },
  "Interrupt": {
    "preferred_term": "Interrupt",
    "definition": "A signal to the processor that indicates the occurrence of an event requiring immediate attention, causing the CPU to temporarily halt its current execution and transfer control to a handler.",
    "definition_status": "defined",
    "introduced_in": null
  }
}
[/TERMINOLOGY]

[CHAPTER]
\section{File System Concepts}
\subsection{Files and Directories}
A \textbf{File} is a named collection of related data stored on secondary storage, identified by a pathname, and accessed via I/O operations. Files are the primary way users interact with persistent data. A \textbf{Directory} is a special file that contains a set of file names and their associated metadata, used to organize files hierarchically. Directories enable the creation of a tree‑like namespace, allowing users to group related files and navigate the storage space efficiently.  
Example: a user may have a directory structure such as \texttt{home/user/documents}.  

\begin{verbatim}
Home
├─ User
│  ├─ Documents
│  └─ Projects
└─ System
\end{verbatim}

\subsection{File System Implementation}
The \textbf{File System} organizes blocks of storage into files and directories. Each file is represented by an \textbf{Inode}, which stores metadata such as file size, permissions, and pointers to the data blocks that hold the file’s contents. The collection of all inodes and block allocations is known as the file system metadata.  

Allocation of storage can be performed using three primary strategies: contiguous, linked, and indexed. Each strategy has distinct trade‑offs in terms of external fragmentation, access speed, and complexity.  

\begin{tabularx}{\textwidth}{@{} l X @{}}
\toprule
Allocation Strategy & Key Characteristics \\
\midrule
Contiguous & All blocks for a file are placed consecutively; simple to allocate but prone to external fragmentation. \\
Linked & File blocks are linked together via pointers; eliminates external fragmentation but incurs extra I/O for pointer retrieval. \\
Indexed & A separate index block stores pointers to all file blocks; supports random access and reduces fragmentation. \\
\bottomrule
\end{tabularx}

\begin{verbatim}
Contiguous Allocation:
+-------------------+
| File Metadata     |
|  -> Start Block   |
+-------------------+
   [B1][B2][B3][B4]  (contiguous blocks)

Linked Allocation:
+-------------------+
| File Metadata     |
|  -> First Block   |
+-------------------+
   [B1] -> [B2] -> [B3] -> [B4] -> NULL

Indexed Allocation:
+-------------------+
| File Metadata     |
|  -> Index Block   |
+-------------------+
   Index Block: ->[B1] ->[B2] ->[B3] ->[B4]
\end{verbatim}

\begin{verbatim}
Indexed Allocation Example
+-------------------+
| Index Block       |
|  -> Block 10      |
|  -> Block 27      |
|  -> Block 33      |
+-------------------+
\end{verbatim}

\subsection{I/O System Overview}
The \textbf{I/O System} manages communication between the computer and external devices. It consists of hardware components, device drivers, and kernel services that together enable data transfer.  

\subsubsection{I/O Hardware}
Physical devices such as disks, keyboards, and network cards are controlled by \textbf{Device Drivers}, which translate generic I/O requests into device‑specific commands. Events that require immediate attention are communicated to the CPU via \textbf{Interrupt} signals, causing the processor to suspend its current task and invoke the appropriate handler.  

\begin{verbatim}
Application --> System Call --> Kernel --> Device Driver --> Hardware
\end{verbatim}

\subsubsection{I/O Software Stack}
The software stack layers these components: user applications issue system calls, the kernel mediates access, device drivers implement the low‑level control, and interrupts notify the CPU of device readiness. This layered approach isolates hardware details from higher‑level code, promoting modularity and portability.  

\subsubsection{I/O Performance}
Performance is influenced by latency (time to begin data transfer) and throughput (amount of data transferred per unit time). Techniques such as buffering, caching, and DMA (Direct Memory Access) are employed to reduce latency and increase throughput.  

\section{I/O System Details}
\subsection{Device Drivers}
A \textbf{Device Driver} encapsulates the logic required to operate a specific hardware device. It provides a uniform interface to the rest of the kernel, handling tasks such as command parsing, status monitoring, and error recovery.  

\subsection{Interrupt Handling}
When an interrupt occurs, the CPU saves its current state, transfers control to an interrupt service routine, processes the event, and then restores the saved state. This mechanism allows the operating system to respond promptly to asynchronous events without polling.  

\begin{verbatim}
[Interrupt] -> [Save State] -> [Jump to ISR] -> [Process Event] -> [Restore State] -> [Resume]
\end{verbatim}

\subsection{Caching and Buffering}
The operating system maintains a cache of recently accessed disk blocks in main memory. A buffer is a temporary storage area that holds data being transferred between the device and memory, reducing the number of direct disk accesses.  

\begin{verbatim}
Application -> System Call -> Kernel
   |                     |
   v                     v
[Cache] <---> [Disk]   [Buffer] <---> [Device]
   ^                     ^
   |                     |
Read requests        Data in transit
\end{verbatim}

\section{Conclusion}
This chapter has explained how file systems organize persistent data and how the I/O system facilitates communication with hardware devices. Mastery of these concepts provides the foundation for understanding more advanced topics such as security mechanisms, protection schemes, and distributed system coordination, which are covered in the next chapter.  

\section*{Tutorial Questions}
\begin{enumerate}
  \item Define a \textit{File} and a \textit{Directory}. Provide an example of a directory hierarchy that includes at least three levels.
  \item Compare contiguous, linked, and indexed allocation strategies in terms of external fragmentation and random‑access performance.
  \item Explain the role of an \textit{Inode} in a Unix‑like file system. What information does it store?
  \item Describe how an \textit{Interrupt} influences the execution flow of an I/O operation.
  \item What is the difference between \textit{caching} and \textit{buffering}? Give a brief example of each.
  \item A user reports slow disk writes. Identify two I/O performance factors that could be causing this issue and suggest a design adjustment for each.
  \item Explain why device drivers are essential for abstracting hardware details from the operating system.
  \item Outline the steps a typical I/O request follows from the application layer to the hardware layer.
\end{enumerate}
\end{CHAPTER}



# Chapter 6: Case Studies and Laboratory Practice


\section{Case Studies}
A \textbf{Case Study} is a detailed examination of a specific instance that illustrates broader operating system concepts. Case studies enable students to analyze real‑world scenarios, identify underlying mechanisms, and draw conclusions about system behavior. They are particularly useful for exploring complex interactions that are difficult to isolate in controlled experiments.

\section{Practical Laboratory Work}
The term \textbf{Laboratory} refers to a structured \textbf{Hands‑on} activity that combines guided instructions with practical tasks. This chapter includes \textbf{Practical Lab Work} that focuses on Linux‑based experiments and simulation projects. Each \textbf{Exercise} is designed to reinforce understanding of a specific concept or technique.

\subsection{Lab Workflow}
\begin{verbatim}
Setup -> Execute -> Collect -> Analyze & Report
\end{verbatim}

\subsection{Hands‑on Linux Exercises}
The following exercise guides students through the configuration of CPU Scheduling policies on a Linux system and the collection of performance metrics.

\begin{verbatim}
# Sample script to run a round‑robin benchmark
taskset -c 0 ./benchmark.sh &
for i in {1..5}; do
    taskset -c 0 ./benchmark.sh &
done
wait
\end{verbatim}

\section{Simulation of Scheduling and Synchronization Algorithms}
The \textbf{Simulation} component models the behavior of scheduling and synchronization mechanisms using a computational framework. This allows exploration of scenarios that are difficult or impractical to reproduce on physical hardware.

\subsection{Simulation Framework}
The framework captures system state, processes events, and records outcomes. It supports both \textbf{Preemptive Scheduling} and \textbf{Non‑preemptive Scheduling}, as well as \textbf{Mutex} and \textbf{Semaphore} synchronization.

\begin{verbatim}
+--------+   +--------+   +--------+   +--------+   +------------+
|  New   |-->|  Ready |-->| Running|-->| Waiting|-->| Terminated |
+--------+   +--------+   +--------+   +--------+   +------------+
\end{verbatim}

\begin{verbatim}
Preemptive Scheduling:
   +-----------------+
   |  CPU running P |
   +-----------------+
            |
            v
   +-----------------+
   |  Timer interrupt|
   +-----------------+
            |
            v
   +-----------------+
   |  Scheduler selects Q |
   +-----------------+

Non-preemptive Scheduling:
   +-----------------+
   |  CPU running P |
   +-----------------+
            |
            v
   +-----------------+
   |  P voluntarily yields |
   +-----------------+
            |
            v
   +-----------------+
   |  Scheduler selects Q |
   +-----------------+
\end{verbatim}

\subsubsection{Simulation Process}
\begin{verbatim}
Simulation Process
      |
      v
+-------------------+
| Load Program      |
+-------------------+
      |
      v
+-------------------+
| Execute Instructions|
+-------------------+
      |
      v
+-------------------+
| Record Events     |
+-------------------+
      |
      v
+-------------------+
| Analyze Results   |
+-------------------+
      |
      v
+-------------------+
| Generate Report   |
+-------------------+
\end{verbatim}

\subsubsection{Example: Round‑Robin Scheduling Simulation}
\begin{verbatim}
# Pseudo‑code for a round‑robin simulator
processes = [P1, P2, P3, P4]
quantum   = 4
ready_q   = queue(processes)

while not ready_q.empty():
    p = ready_q.dequeue()
    execute(p, min(quantum, p.remaining_time))
    if p.remaining_time > quantum:
        p.remaining_time -= quantum
        ready_q.enqueue(p)
    else:
        p.remaining_time = 0
        p.state = TERMINATED
        record(p)
\end{verbatim}

\begin{verbatim}
[ P1 ] -> [ P2 ] -> [ P3 ] -> [ P4 ] -> (loop)
\end{verbatim}

\begin{table}[ht]
\centering
\begin{tabularx}{\textwidth}{@{} l X @{}}
\toprule
Approach & Key Characteristics \\
\midrule
Case Study & In‑depth analysis of a single instance; focuses on context and detailed observation. \\
Laboratory & Controlled setting for repeated experimentation; emphasizes hands‑on execution. \\
Simulation & Abstract model that mimics system behavior; enables exploration beyond physical limits. \\
\bottomrule
\end{tabularx}
\end{table}

\section{Conclusion}
The practical experiences described in this chapter provide a solid foundation for further research in system optimization and advanced operating system design. The techniques and methodologies introduced here will be built upon in future studies involving performance modeling and system verification.

\section*{Tutorial Questions}
\begin{enumerate}
\item Describe the purpose of a case study in operating systems education. Provide an example from this chapter.
\item Explain the steps involved in conducting a hands‑on Linux exercise to evaluate CPU Scheduling. 
\item Compare two scheduling algorithms using a simulation scenario. Which algorithm performed better under high load and why? 
\item Identify a common race condition that can arise during a synchronization simulation and propose a synchronization primitive to prevent it. 
\item Explain how a monitor can be used to enforce mutual exclusion in a simulated critical section. 
\item Discuss the role of a lab report in documenting the results of a scheduling simulation. List its essential sections. 
\item Provide an example of a practical lab exercise that investigates virtual memory paging. What metrics would you measure? 
\item Explain the difference between preemptive and non‑preemptive scheduling in the context of a simulation. How does each affect the simulation logic? 
\end{enumerate}


