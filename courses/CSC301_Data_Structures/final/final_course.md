# Chapter 1: discuss the appropriate use of built-in data structures;


Computer programs manipulate data to solve real-world problems. The organization of data in computer memory directly dictates how efficiently algorithms can access, search, insert, and delete records. High-level programming languages provide \textbf{built-in data structures}, which are pre-packaged, highly optimized collection types supported natively by the language runtime and standard library.

Understanding the underlying mechanics of built-in data structures is vital for software performance and correctness. Selecting an inappropriate structure, such as using a dynamic array for frequent membership checks across millions of records, can transform a sub-second operation into an execution bottleneck lasting minutes. Knowing when to utilize each built-in structure enables engineers to write clean, performant code without reinventing common data management patterns.

This chapter examines the core built-in data structures found across modern high-level programming languages, including static arrays, dynamic arrays, tuples, dictionaries, and sets. It analyzes their physical memory layouts, operational time complexities, and behavioral trade-offs. Mastering these foundational structures provides the essential context required for object-oriented data structure design and formal algorithm analysis in subsequent chapters.

\section{Memory Layout and Fundamental Characteristics}

Built-in data structures organize data in physical system memory according to specific layout paradigms. These paradigms govern how memory is allocated, accessed, and modified during program execution.

\subsection{Contiguous versus Non-Contiguous Allocation}

Memory allocation strategies are broadly divided into contiguous and non-contiguous arrangements. A \textbf{contiguous memory allocation} reserves a single, uninterrupted block of physical memory addresses for storing data elements. Because elements sit directly adjacent to one another, the memory address of the $i$-th element can be calculated directly from the base memory address of the structure using constant time address arithmetic:

\begin{equation}
\text{Address}(i) = \text{Base Address} + (i \times \text{Element Size})
\end{equation}

In contrast, non-contiguous memory allocation distributes data elements across arbitrary memory locations linked together via memory pointers. While non-contiguous structures facilitate dynamic resizing without reallocating full blocks, they lose the ability to perform constant-time random access by integer index and incur additional pointer overhead.

\subsection{Mutability and Structural Invariance}

Data structures are classified by whether their contents or dimensions can change after initialization. A \textbf{mutable} structure allows modification, addition, or removal of elements in place without allocating a new structure in memory. Dynamic arrays and dictionaries are primary examples of mutable built-in structures.

An \textbf{immutable} structure cannot be modified once created. Any transformation applied to an immutable structure creates a completely new instance in memory. Immutability provides inherent thread safety and guarantees structural invariance, making immutable built-in structures like tuples ideal for read-only configurations, dictionary keys, and concurrent execution contexts.

\begin{verbatim}
Static Array Layout (Fixed Memory Block = 4 Elements):
+-----------------+-----------------+-----------------+-----------------+
| Address: 0x1000 | Address: 0x1004 | Address: 0x1008 | Address: 0x100C |
| Index: 0        | Index: 1        | Index: 2        | Index: 3        |
| Value: 42       | Value: 87       | Value: 15       | Value: 93       |
+-----------------+-----------------+-----------------+-----------------+

Dynamic Array Layout (Logical Size = 3, Allocated Capacity = 6):
+-------+-------+-------+-------------------+-------------------+-------------------+
| Ind: 0| Ind: 1| Ind: 2| Unallocated Space | Unallocated Space | Unallocated Space |
| Val: A| Val: B| Val: C| (Reserved Buffer) | (Reserved Buffer) | (Reserved Buffer) |
+-------+-------+-------+-------------------+-------------------+-------------------+
^ Base Pointer           ^ Next Insertion Point
\end{verbatim}

\section{Linear Built-in Data Structures}

Linear data structures maintain a sequential ordering among their elements, where each element has a distinct predecessor and successor (except for the boundary elements).

\subsection{Static Arrays}

A static \textbf{array} is a fixed-size, contiguous sequence of elements of a single uniform data type. The total capacity of a static array must be known at allocation time and cannot grow or shrink during program execution.

Because all elements share identical byte sizes, static arrays support direct constant-time indexed access, denoted as $O(1)$. However, inserting or deleting elements at arbitrary positions requires shifting subsequent elements, resulting in linear time complexity, $O(n)$, where $n$ is the number of elements.

\subsection{Dynamic Arrays}

A \textbf{dynamic array} provides contiguous sequential storage similar to a static array but automatically resizes itself when capacity is exhausted. Popular high-level language implementations include Python \texttt{list}, Java \texttt{ArrayList}, and C++ \texttt{std::vector}.

To minimize the overhead of frequent allocations, dynamic arrays utilize a growth factor strategy. When an element is added to a full array, the underlying execution environment performs the following sequence:
\begin{enumerate}
    \item Allocates a new contiguous memory block, typically twice the size of the existing block (growth factor of 2).
    \item Copies all existing elements from the old memory block to the new memory block.
    \item Releases the old memory block back to the system allocator.
    \item Inserts the new element into the next available slot.
\end{enumerate}

\begin{verbatim}
Dynamic Array Growth and Reallocation Sequence:

Step 1: Array is Full (Capacity = 4, Size = 4)
+---+---+---+---+
| A | B | C | D |  (Old Memory Block)
+---+---+---+---+

Step 2: Append 'E' triggers allocation of new expanded block (Capacity = 8)
+---+---+---+---+---+---+---+---+
|   |   |   |   |   |   |   |   |  (New Memory Block)
+---+---+---+---+---+---+---+---+

Step 3: Copy existing elements and insert 'E'
+---+---+---+---+---+---+---+---+
| A | B | C | D | E |   |   |   |  (Size = 5, Capacity = 8)
+---+---+---+---+---+---+---+---+
                 ^ Next Insertion Point

Step 4: Release old memory block back to heap allocator
\end{verbatim}

Although individual resizing operations require $O(n)$ copy operations, amortized analysis proves that appending an element to a dynamic array executes in $O(1)$ time on average over a sequence of appends.

\subsection{Tuples}

A \textbf{tuple} is an ordered, immutable collection of elements. Unlike standard static arrays, tuples can store heterogeneous data types across their slots while maintaining fixed positional semantics.

Because tuples are immutable, the runtime allocates exact memory blocks with zero dynamic overhead or growth buffers. This makes tuples memory-efficient and faster to instantiate than dynamic arrays. Tuples are predominantly used to group related data fields together (such as database rows or multi-value function returns) without creating custom class abstractions.

\section{Associative and Set Structures}

Associative and set structures organize data based on logical keys or content values rather than sequential integer positioning.

\subsection{Dictionaries and Hash Maps}

A \textbf{dictionary} (also called a hash map or associative array) is an unordered collection of key-value pairs, where each key must be unique and immutable. Dictionaries allow programs to retrieve values rapidly using their associated keys rather than scanning through an entire dataset sequentially.

Internally, dictionaries rely on a mathematical function called a \textbf{hash function}. The hash function accepts a key as input and computes an integer hash code, which maps directly to a specific slot (bucket) within an underlying array.

\begin{verbatim}
Dictionary Hash-Based Lookup Mechanism:

Key: "OSUN_ID_402"
       |
       v
[ Hash Function ]  ====> Computed Bucket Index: 3
       |
       v
Underlying Bucket Array:
+---+------------------------------------+
| 0 | Empty                              |
+---+------------------------------------+
| 1 | Key: "OSUN_ID_101" -> Value: "A+"  |
+---+------------------------------------+
| 2 | Empty                              |
+---+------------------------------------+
| 3 | Key: "OSUN_ID_402" -> Value: "B"   |  <=== Match Found (O(1) Access)
+---+------------------------------------+
\end{verbatim}

When two distinct keys produce the same bucket index, a hash collision occurs. Dictionaries resolve collisions using collision handling strategies such as \textbf{chaining} (maintaining a linked list per bucket) or \textbf{open addressing} (probing subsequent array slots). When a high-quality hash function is used, search, insertion, and deletion operations execute in $O(1)$ average time complexity.

\subsection{Sets}

A \textbf{set} is an unordered collection of unique elements. Sets mirror the mathematical properties of set theory, preventing duplicate values from existing within the same container.

Most language libraries implement sets using hash table backends (where elements serve as keys mapped to dummy values) or balanced search trees. Hash-based set implementations offer $O(1)$ average time complexity for insertion, deletion, and membership testing. Sets also provide direct, built-in operations for union ($\cup$), intersection ($\cap$), and difference ($\setminus$).

\section{Comparative Performance Analysis and Selection Criteria}

Choosing the correct built-in data structure requires balancing time complexity, space overhead, and programmatic constraints. Table~\ref{tab:builtin_comparison} summarizes the asymptotic operational characteristics of fundamental built-in data structures.

\begin{table}[htbp]
\centering
\caption{Operational Complexity and Characteristics of Built-in Data Structures}
\label{tab:builtin_comparison}
\begin{tabularx}{\textwidth}{X >{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{2.8cm}}
\toprule
\textbf{Data Structure} & \textbf{Access by Index} & \textbf{Search by Value} & \textbf{Insertion / Deletion} & \textbf{Primary Use Case} \\
\midrule
Static Array & $O(1)$ & $O(n)$ & $O(n)$ & Fixed-size numeric or fixed-length sequences. \\
Dynamic Array & $O(1)$ & $O(n)$ & $O(1)$ Amortized (at end) & General-purpose ordered sequences with variable size. \\
Tuple & $O(1)$ & $O(n)$ & Not Supported (Immutable) & Fixed multi-attribute records and composite lookup keys. \\
Dictionary & Not Supported & $O(1)$ Average & $O(1)$ Average & Rapid key-value lookups and relational mapping. \\
Set & Not Supported & $O(1)$ Average & $O(1)$ Average & Uniqueness enforcement and fast membership checks. \\
\bottomrule
\end{tabularx}
\end{table}

To determine the optimal data structure for a given task, consider the following structural decision pipeline:

\begin{verbatim}
Structural Selection Decision Tree:

                    [ Select Structure ]
                             |
             Does data consist of Key-Value pairs?
                    /                 \
                 (Yes)                (No)
                  /                     \
            [Dictionary]      Must duplicates be excluded?
                                    /           \
                                 (Yes)          (No)
                                  /               \
                               [Set]       Is collection size/content fixed?
                                                /              \
                                             (Yes)             (No)
                                              /                  \
                                      [Static Array /       [Dynamic Array]
                                           Tuple]
\end{verbatim}

\begin{enumerate}
    \item \textbf{Identity versus Association:} If data items are indexed by natural sequential integers, select a dynamic array or static array. If data items are retrieved via unique identifiers (strings, UUIDs, compound keys), select a dictionary.
    \item \textbf{Uniqueness Requirements:} If duplicate elements must be filtered out automatically or membership tests occur frequently, select a set.
    \item \textbf{Mutability Constraints:} If the collection must remain fixed after creation to prevent accidental modification, select a tuple.
    \item \textbf{Access Pattern Optimization:} If elements are accessed via arbitrary integer positions, prioritize linear contiguous structures to leverage hardware CPU cache lines.
\end{enumerate}

\section{Worked Examples}

The following concrete engineering scenarios illustrate how to evaluate and select built-in data structures based on performance requirements.

\subsection{Worked Example 1: Efficient Student Record Management}

\textbf{Problem Statement:} A university registrar system receives continuous batches of student records. The system must perform two core tasks efficiently:
\begin{enumerate}
    \item Retrieve student details instantly given a unique 8-digit Student Identification Number (Matric Number).
    \item Maintain a log of incoming records in the exact order they arrive for auditing purposes.
\end{enumerate}

\textbf{Analysis and Solution:}
Using a dynamic array for Task 1 requires scanning elements sequentially, yielding an $O(n)$ search time. For 100,000 students, scanning the array repeatedly creates severe performance penalties.

To achieve optimal performance, the system should combine two complementary built-in structures:
\begin{itemize}
    \item \textbf{Dictionary for Fast Lookups:} Map each unique Matric Number (string key) to the corresponding student record object (value). This provides $O(1)$ average time retrieval for Task 1.
    \item \textbf{Dynamic Array for Audit Logging:} Append incoming student record references sequentially to a dynamic array. This preserves insertion order and completes Task 2 in $O(1)$ amortized time per insertion.
\end{itemize}

\subsection{Worked Example 2: Filtering Duplicate IP Addresses}

\textbf{Problem Statement:} A web server security daemon processes a log stream containing 10,000,000 IP address records. The log contains many repeating IP addresses. The daemon must compute the exact number of unique IP addresses present in the log and check whether specific suspicious IP addresses are present.

\textbf{Analysis and Solution:}
If a dynamic array is used, checking if an IP address is already recorded requires searching through existing elements, taking $O(k)$ time for an array of size $k$. Building the unique list across $n$ log entries takes $O(n^2)$ total operations:

$$\text{Total Operations} = \sum_{k=1}^{n} k = \frac{n(n + 1)}{2} \approx 5 \times 10^{13} \text{ operations}$$

By choosing a \textbf{Set} structure instead:
\begin{enumerate}
    \item Each IP address string is inserted into the set. The set hashes the string and performs insertion in $O(1)$ average time. Duplicates are discarded automatically.
    \item Total time complexity to process $n$ entries drops to $O(n)$, executing roughly $10^7$ operations instead of $5 \times 10^{13}$.
    \item Subsequent queries checking whether a suspicious IP exists execute in $O(1)$ average time.
\end{enumerate}

\section{Summary and Next Steps}

Built-in data structures form the essential execution foundation of software applications. Arrays and dynamic arrays provide fast index-based positional access; tuples enforce immutability and record integrity; dictionaries enable constant-time key-based lookup; and sets optimize uniqueness checking and set-theoretic operations. Choosing the appropriate structure based on temporal and spatial complexity prevents severe performance bottlenecks.

While built-in data structures solve standard data management problems, complex domains often demand domain-specific data structures with customized behavior. The next chapter introduces object-oriented programming concepts, demonstrating how encapsulation, inheritance, and polymorphism enable engineers to build robust, custom data abstractions.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Explain the fundamental memory organization difference between contiguous and non-contiguous data structures. Identify how this difference impacts index-based element access time.
    \item A software developer uses a dynamic array to store historical transaction records. Describe the internal steps taken by the runtime environment when an item is added to a dynamic array that has reached its maximum allocated capacity. What is the amortized time complexity of this operation?
    \item Compare and contrast a tuple and a dynamic array across three distinct technical dimensions: memory allocation efficiency, mutability, and primary software usage cases.
    \item An application performs frequent membership queries ("does item $X$ exist in collection $C$?") on a dataset containing 2,000,000 records. Evaluate the operational efficiency of performing this query using a dynamic array versus a set. Provide big-O notation complexities for both approaches.
    \item Explain how a dictionary achieves $O(1)$ average time complexity for value retrieval. What condition causes this performance to degrade to $O(n)$, and how do modern hashing implementations mitigate this risk?
    \item A system tracks live vehicle positions using geographical coordinate pairs (latitude, longitude). These coordinates must be updated continuously, but specific route history checkpoints must remain permanent and unalterable. Recommend the built-in data structure best suited for storing live coordinates versus permanent route checkpoints, justifying your selection for each.
    \item Analyze the computational complexity trade-offs involved when using a static array versus a dynamic array in a memory-constrained embedded system with known, fixed bounds.
\end{enumerate}



# Chapter 2: apply object-oriented concepts (inheritance, polymorphism, design patterns, etc.) in


Data structures serve as the structural backbone of software systems, defining how memory is organized and manipulated. However, raw data structures written without proper abstraction mechanisms can become tightly coupled to specific programs, making code difficult to maintain, extend, or reuse. Object-oriented programming provides architectural principles that decouple abstract behavioral contracts from concrete physical layouts.

This chapter examines how key object-oriented concepts, specifically inheritance, polymorphism, and design patterns, are applied to data structure design. By leveraging these concepts, developers can construct modular data structure libraries that decouple client interfaces from underlying operational mechanics.

Understanding these abstraction techniques is essential for modern software development. Building upon the built-in data structures explored in Chapter 1, this material establishes the structural patterns used to build custom, extensible data structures in Chapter 3 and beyond.

\section{Object-Oriented Abstraction and Abstract Data Types}

In software development, an \textbf{abstract data type} (ADT) is a mathematical specification of a collection of data and the operations that can be performed on that data. An ADT defines \textit{what} operations are available, their parameters, and their expected outcomes, without specifying \textit{how} those operations are implemented in memory. A concrete data structure, by contrast, is the physical implementation of an ADT in code, specifying data fields, memory allocation strategies, and algorithmic routines.

Object-oriented programming enforces ADT specifications through encapsulation and access control. Encapsulation isolates the internal memory representation of a data structure behind a public interface. Private fields prevent external code from directly modifying pointer references or array indices, preserving internal structural invariants.

\subsection{Separating Specification from Implementation}

Consider a sequence of elements accessible by index. The ADT specification defines operations such as insertion, removal, search, and size retrieval. Multiple distinct concrete data structures can satisfy this same specification:

\begin{itemize}
    \item A \textbf{dynamic array}, which stores elements in contiguous memory and offers fast positional access.
    \item A linked list, which stores elements in disjoint nodes connected by pointers, offering fast insertions at node boundaries.
\end{itemize}

By defining an abstract base class or interface, client programs can operate directly on the abstraction. This allows software systems to substitute concrete representations without altering the client code that depends on them.

\begin{verbatim}
+-------------------------------------------------------+
|                    <<Interface>>                      |
|                       ListADT                         |
+-------------------------------------------------------+
| + add(element: T): void                               |
| + remove(index: int): T                               |
| + get(index: int): T                                  |
| + size(): int                                         |
+-------------------------------------------------------+
                           ^
                           |
            +--------------+--------------+
            |                             |
+-----------------------+     +-----------------------+
|     ArrayList<T>      |     |     LinkedList<T>     |
+-----------------------+     +-----------------------+
| - data: T[]           |     | - head: Node<T>       |
| - capacity: int       |     | - tail: Node<T>       |
| - count: int          |     | - count: int          |
+-----------------------+     +-----------------------+
\end{verbatim}

\section{Inheritance and Polymorphism in Data Structure Design}

\textbf{Inheritance} is an object-oriented mechanism where a child class acquires fields and methods from a parent class. In data structure engineering, inheritance serves two primary roles: code reuse and subtype specification.

Subtyping inheritance defines formal class hierarchies where child classes fulfill the contract of a parent type. Implementation inheritance allows derived classes to inherit common operational logic, reducing duplicate code across related structures.

\textbf{Polymorphism} enables objects of different concrete classes to respond to the same method call in class-specific ways. Through dynamic method dispatch, the runtime environment inspects the concrete type of an object and invokes the corresponding method implementation.

\subsection{Class Hierarchies and Code Sharing}

Inheritance hierarchies prevent redundancy by placing shared operational logic high in the class tree. An abstract base class can implement operations that depend only on other abstract primitives.

For example, an abstract list base class can provide a concrete implementation of an \texttt{isEmpty()} method that checks if \texttt{size() == 0}. Subclasses inheriting this base class receive \texttt{isEmpty()} automatically, needing only to implement the storage-specific \texttt{size()} method.

\begin{table}[htbp]
\centering
\caption{Comparison of Inheritance and Composition in Data Structure Design}
\label{tab:inheritance_vs_composition}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.5cm} X X}
\toprule
\textbf{Dimension} & \textbf{Inheritance ("is-a")} & \textbf{Composition ("has-a")} \\
\midrule
Relationship & Establishes a rigid subtype hierarchy between parent and child classes. & Embeds an instance of another data structure as an internal field. \\
Coupling & High coupling; modifications to base classes affect all derived classes. & Low coupling; the encapsulated instance can be swapped independently. \\
Flexibility & Static; behavior is determined at compile time by class definitions. & Dynamic; contained objects and strategy delegates can be updated at runtime. \\
Primary Purpose & Defining shared interface contracts and inheriting shared implementations. & Building complex or restricted structures from simple components. \\
\bottomrule
\end{tabularx}
\end{table}

While inheritance creates tight coupling between base and child classes, composition embeds a data structure inside another class, delegating work to the internal object. Designing data structures often requires choosing between inheritance and composition to maintain flexibility.

\section{Applying Design Patterns to Data Structures}

\textbf{Design patterns} are reusable, generalized software engineering solutions to recurring design problems within a given domain. Applying design patterns to data structures yields modular, flexible implementations that adapt easily to changing requirements.

Four essential design patterns used extensively in data structure design are:

\begin{enumerate}
    \item \textbf{Iterator Pattern}: Traverses aggregate elements sequentially without exposing internal structural representations.
    \item \textbf{Factory Pattern}: Encapsulates object creation mechanics for nodes and structural components.
    \item \textbf{Strategy Pattern}: Parameterizes key algorithmic behaviors within a data structure.
    \item \textbf{Adapter Pattern}: Converts an existing data structure interface into an interface expected by client code.
\end{enumerate}

\subsection{The Iterator Pattern}

The \textbf{iterator pattern} separates element traversal from the internal layout of a collection. Without an iterator, client code traversing a linked list must manually navigate pointers, while traversing an array requires array index management.

An iterator provides a unified, sequential interface featuring operations such as \texttt{hasNext()} and \texttt{next()}. Client code can iterate over arrays, trees, or graphs using identical loop structures.

\begin{verbatim}
+--------------------+                       +--------------------+
|   <<Interface>>    |                       |   <<Interface>>    |
|    Iterable<T>     |                       |    Iterator<T>     |
+--------------------+                       +--------------------+
| + iterator()       |                       | + hasNext(): bool  |
+--------------------+                       | + next(): T        |
          ^                                  +--------------------+
          |                                            ^
          |                                            |
+--------------------+   instantiates        +--------------------+
|   ConcreteList     |---------------------->|  ConcreteIterator  |
+--------------------+                       +--------------------+
\end{verbatim}

The iterator preserves data structure integrity by preventing client code from modifying internal pointers directly during traversal.

\subsection{The Factory Pattern}

The \textbf{factory pattern} delegates object instantiation to dedicated methods or builder classes. In complex data structures, creating nodes or structural elements directly inside algorithms couples the structure to concrete node classes.

For example, a balanced search tree class can use a factory method, \texttt{createNode(key, value)}, to generate tree nodes. Subclasses override this factory method to instantiate specialized nodes, such as Red-Black nodes containing color bits, without altering the core search tree logic.

\subsection{The Strategy Pattern}

The \textbf{strategy pattern} encapsulates interchangeable algorithms into separate classes conforming to a shared interface. Data structures often rely on external algorithms to drive internal behavior, including:

\begin{itemize}
    \item Custom comparison operations for sorting and heap ordering.
    \item Alternative hash functions for hash tables.
    \item Dynamic resizing strategies for dynamic arrays.
\end{itemize}

By passing a strategy object to a data structure during construction, the structure's runtime behavior can be changed without modifying its source code.

For instance, a dynamic array can accept a growth strategy interface. One strategy can grow capacity multiplicatively by doubling ($1.5\times$ or $2.0\times$), while another increases capacity linearly by fixed increments.

\begin{verbatim}
+-----------------------+                    +--------------------------------+
|    DynamicArray<T>    |                    |         <<Interface>>          |
+-----------------------+                    |        ResizingStrategy        |
| - strategy: Strategy  |------------------->+--------------------------------+
| - capacity: int       |                    | + getNextCapacity(curr): int   |
+-----------------------+                    +--------------------------------+
| + resize(): void      |                                    ^
+-----------------------+                                    |
                                           +-----------------+-----------------+
                                           |                                   |
                             +---------------------------+       +---------------------------+
                             |  MultiplicativeStrategy   |       |     AdditiveStrategy      |
                             +---------------------------+       +---------------------------+
                             | + getNextCapacity(): int  |       | + getNextCapacity(): int  |
                             +---------------------------+       +---------------------------+
\end{verbatim}

\subsection{The Adapter Pattern}

The \textbf{adapter pattern} converts the interface of an existing class into a different interface expected by a client. This pattern is commonly used to implement restricted access data structures, such as Stacks and Queues, using existing linear structures.

Consider implementing a Stack ADT using a dynamic array. A Stack requires \texttt{push()}, \texttt{pop()}, and \texttt{peek()} operations, whereas a dynamic array exposes indexed access operations like \texttt{addAt()}, \texttt{removeAt()}, and \texttt{get()}. The Stack adapter class wraps an internal dynamic array instance, translating stack operations into array actions.

\begin{verbatim}
class StackAdapter<T>:
    private list: DynamicArray<T>

    constructor():
        list = new DynamicArray<T>()

    method push(item: T): void:
        list.addLast(item)

    method pop(): T:
        if list.isEmpty():
            throw UnderflowException
        return list.removeLast()

    method peek(): T:
        if list.isEmpty():
            throw UnderflowException
        return list.get(list.size() - 1)
\end{verbatim}

\section{Performance Trade-Offs and Architectural Considerations}

Applying object-oriented abstractions to data structures introduces performance trade-offs that must be evaluated against engineering advantages.

\begin{table}[htbp]
\centering
\caption{Summary of Core Design Patterns in Data Structure Design}
\label{tab:design_patterns_summary}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{2.0cm} X X}
\toprule
\textbf{Pattern} & \textbf{Category} & \textbf{Structural Context} & \textbf{Primary Benefit} \\
\midrule
Iterator & Behavioral & Collection element traversal. & Decouples collection traversal from internal layout. \\
Factory & Creational & Node and container creation. & Encapsulates object creation and enables specialization. \\
Strategy & Behavioral & Hashing, growth, and sorting routines. & Enables runtime selection of dynamic algorithms. \\
Adapter & Structural & Stack, Queue, and Deque construction. & Reuses existing container code via interface transformation. \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Virtual Method Overhead and Memory Layout}

Dynamic polymorphism requires runtime method dispatch. In languages that compile to virtual machine bytecode or native binaries, polymorphic calls use virtual method tables (vtables) to locate method pointers at runtime. This indirect call mechanism introduces minor latency compared to direct function calls and can prevent CPU compiler optimizations such as inline expansion.

Additionally, object-oriented abstractions introduce memory overhead:

\begin{itemize}
    \item Object headers: Language runtimes attach metadata, such as type indicators and synchronization locks, to every object instance.
    \item Indirection and cache performance: Storing collections of objects via pointer references can cause CPU cache misses due to disjoint memory locations, compared to contiguous arrays of primitive data types.
\end{itemize}

\begin{verbatim}
Contiguous Primitive Array Layout (Cache-Friendly):
+---------+---------+---------+---------+
| Data 1  | Data 2  | Data 3  | Data 4  |
+---------+---------+---------+---------+

Reference-Based Object Layout (Pointer Indirection):
+---------+---------+---------+---------+
| Ref 1   | Ref 2   | Ref 3   | Ref 4   |
+----+----+----+----+----+----+----+----+
     |         |         |         |
     v         v         v         v
  +-----+   +-----+   +-----+   +-----+
  |Obj 1|   |Obj 2|   |Obj 3|   |Obj 4|
  +-----+   +-----+   +-----+   +-----+
\end{verbatim}

Engineers must weigh clean architectural design against low-level execution speed. For general application development, object-oriented abstractions improve code maintainability, safety, and reusability. In performance-critical systems, direct memory layouts and simplified procedural abstractions may be preferred.

\section{Summary}

Object-oriented programming concepts provide tools for engineering reusable data structure libraries. Abstract data types separate interface definitions from concrete storage mechanics. Inheritance establishes formal type hierarchies and shares common implementations, while polymorphism allows applications to manipulate collections generically. Design patterns like Iterator, Factory, Strategy, and Adapter solve common architectural problems, improving data structure flexibility and reuse.

These principles pave the way for Chapter 3, where we will build fundamental data structures, including stacks, queues, linked lists, trees, and graphs, from the ground up using object-oriented principles.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Explain the distinction between an Abstract Data Type (ADT) and a concrete data structure. Provide two distinct concrete data structure examples for a single ADT specification.
    \item Describe how encapsulation helps protect the internal structural invariants of a complex data structure. What vulnerabilities arise when internal representation details are exposed?
    \item Compare inheritance ("is-a") and composition ("has-a") as techniques for constructing new data structures. In what scenario is composition preferred over inheritance?
    \item Illustrate the Iterator Pattern using a class diagram or pseudocode. How does the iterator pattern decouple client code from the physical storage representation of a collection?
    \item An engineer needs to implement a bounded Queue structure using an existing \texttt{DynamicArray} class. Identify which design pattern should be applied, write pseudocode for the class wrapper, and explain how the wrapper enforces queue behavior.
    \item Discuss the Strategy Pattern in the context of dynamic array resizing. Design a scenario where switching dynamic array growth strategies at runtime improves performance or memory efficiency.
    \item Analyze the performance costs associated with applying polymorphism and abstract interface abstractions to high-performance data structures. Identify two computational or memory overheads introduced by object-oriented abstraction layers.
\end{enumerate}



# Chapter 3: implement various data structures and their algorithms, and apply them in implementing


Building upon the abstract data types and object-oriented design patterns introduced in prior chapters, software systems require concrete underlying implementations to manage memory and execute operations efficiently. While high-level programming environments provide built-in data structures, constructing these structures directly exposes fundamental trade-offs between memory layout, access overhead, and algorithmic complexity.

This chapter examines the internal mechanics, structural implementations, and algorithmic operations of core data structures: linked lists, stacks, queues, binary search trees, and hash tables. Mastering these low-level implementations provides the operational insight needed to evaluate execution bottlenecks, avoid hidden overheads, and build custom data organizations for complex software applications.

\section{Pointer-Based Linear Structures: Linked Lists}

Linear data structures organize elements in a sequential order. Arrays allocate contiguous blocks of memory, whereas pointer-based lists distribute elements dynamically across non-contiguous physical memory locations.

\subsection{Singly Linked Lists}

A **singly linked list** consists of a sequence of nodes where each node contains two distinct fields: a data element and a reference pointer to the next node in the sequence. The structure is anchored by a \texttt{head} pointer that points to the first node. The terminal node contains a \texttt{null} reference to signal the end of the list.

\begin{verbatim}
Singly Linked List Memory Layout:

 +------+------+    +------+------+    +------+------+
 | Data | Next |--->| Data | Next |--->| Data | Null |
 +------+------+    +------+------+    +------+------+
   ^
   |
 Head
\end{verbatim}

Primary operations on a singly linked list operate via pointer manipulation:
\begin{itemize}
    \item \textbf{Insertion at Head}: A new node is allocated, its \texttt{next} pointer is directed to the current \texttt{head}, and the \texttt{head} pointer is updated to point to the new node. This operates in $O(1)$ constant time.
    \item \textbf{Traversal and Search}: Accessing an element at index $k$ requires traversing $k$ pointer references sequentially starting from \texttt{head}. This operation requires $O(n)$ linear time.
    \item \textbf{Deletion}: Removing a target node requires updating the \texttt{next} pointer of its preceding node to bypass the target node and point directly to the target node's successor. Locating the predecessor requires $O(n)$ search time, but the link modification itself is $O(1)$.
\end{itemize}

\subsection{Doubly Linked Lists}

A **doubly linked list** expands the node design by incorporating two pointers per node: a \texttt{next} pointer referencing the successor node and a \texttt{prev} pointer referencing the predecessor node. A \texttt{tail} pointer is maintained alongside the \texttt{head} pointer to anchor both ends of the structure.

\begin{verbatim}
Doubly Linked List Memory Layout:

       +------+------+------+    +------+------+------+
Null <-| Prev | Data | Next |<---| Prev | Data | Next |---> Null
       +------+------+------+--->+------+------+------+
         ^                          ^
         |                          |
        Head                       Tail
\end{verbatim}

Bidirectional pointers eliminate the need to traverse from the head when searching for a preceding node during deletion. Given a direct pointer reference to a node $P$ within a doubly linked list, $P$ can be removed in $O(1)$ time by setting $P.\texttt{prev}.\texttt{next} = P.\texttt{next}$ and $P.\texttt{next}.\texttt{prev} = P.\texttt{prev}$. However, this additional pointer maintenance increases the per-node dynamic memory overhead.

\subsection{Worked Example: Deletion in a Doubly Linked List}

Consider a doubly linked list containing nodes $A \leftrightarrow B \leftrightarrow C$. To delete target node $B$:
\begin{enumerate}
    \item Access node $A$ via $B.\texttt{prev}$ and node $C$ via $B.\texttt{next}$.
    \item Update node $A$'s forward reference: $A.\texttt{next} \leftarrow C$.
    \item Update node $C$'s backward reference: $C.\texttt{prev} \leftarrow A$.
    \item Clear node $B$'s internal pointers: $B.\texttt{next} \leftarrow \texttt{null}$, $B.\texttt{prev} \leftarrow \texttt{null}$.
    \item Release memory allocated for node $B$.
\end{enumerate}

\section{Restricted Linear Structures: Stacks and Queues}

Stacks and queues apply specific constraints to element access and ordering, abstracting insertion and removal into well-defined interface behaviors.

\subsection{Stacks}

A **stack** is a linear data structure operating under a Last-In, First-Out (LIFO) protocol. Elements can only be added or removed from a single end, designated as the top of the stack.

The core operations are:
\begin{itemize}
    \item \texttt{push(item)}: Places a new item onto the top of the stack.
    \item \texttt{pop()}: Removes and returns the top item from the stack.
    \item \texttt{peek()}: Returns the top item without modifying the stack.
\end{itemize}

A stack can be implemented using either a dynamic array or a singly linked list. In an array-based implementation, the top is tracked by an integer index, yielding $O(1)$ amortized push operations and $O(1)$ pop operations. In a linked list implementation, push and pop operations perform node insertion and removal at the list head in deterministic $O(1)$ time.

\begin{verbatim}
Stack Conceptual Structure:

      +----------+
      |  Item C  |  <-- Top of Stack (Push / Pop)
      +----------+
      |  Item B  |
      +----------+
      |  Item A  |
      +----------+
\end{verbatim}

\subsection{Queues}

A **queue** is a linear data structure operating under a First-In, First-Out (FIFO) protocol. Elements are inserted at the rear and removed from the front.

The core operations are:
\begin{itemize}
    \item \texttt{enqueue(item)}: Appends an element to the rear of the queue.
    \item \texttt{dequeue()}: Removes and returns the element at the front of the queue.
\end{itemize}

Implementing a queue via a standard contiguous array can cause performance issues if dequeue operations shift remaining elements left, incurring $O(n)$ cost per operation. To maintain $O(1)$ operations, arrays are implemented as **circular queues**, where two index pointers (\texttt{front} and \texttt{rear}) wrap around the physical boundaries using modular arithmetic:
$$\text{rear} = (\text{rear} + 1) \pmod{\text{capacity}}$$

\begin{verbatim}
Circular Queue Array Implementation:

Array Indices:   0     1     2     3     4
              +-----+-----+-----+-----+-----+
Contents:     |  D  |  E  |     |  A  |  C  |
              +-----+-----+-----+-----+-----+
                   ^                 ^
                   |                 |
                 Rear              Front
\end{verbatim}

\subsection{Worked Example: Postfix Expression Evaluation using a Stack}

Postfix notation (Reverse Polish Notation) eliminates the need for parentheses in arithmetic expressions by placing operators immediately after their operands. Evaluators process postfix strings sequentially from left to right using a stack:
\begin{itemize}
    \item If a value is an operand, push it onto the stack.
    \item If a value is an operator, pop two operands from the stack, apply the operator (the second popped value is the left operand), and push the result back onto the stack.
\end{itemize}

Evaluate the postfix expression: $6 \quad 2 \quad 3 \quad * \quad + \quad 4 \quad -$

\begin{table}[h!]
\centering
\caption{Step-by-step Evaluation of $6 \quad 2 \quad 3 \quad * \quad + \quad 4 \quad -$}
\label{tab:postfix_trace}
\begin{tabularx}{\textwidth}{c c X l}
\toprule
\textbf{Step} & \textbf{Token} & \textbf{Action} & \textbf{Stack State (Bottom to Top)} \\
\midrule
1 & $6$ & Push $6$ & $[6]$ \\
2 & $2$ & Push $2$ & $[6, 2]$ \\
3 & $3$ & Push $3$ & $[6, 2, 3]$ \\
4 & $*$ & Pop $3, 2$; Evaluate $2 * 3 = 6$; Push $6$ & $[6, 6]$ \\
5 & $+$ & Pop $6, 6$; Evaluate $6 + 6 = 12$; Push $12$ & $[12]$ \\
6 & $4$ & Push $4$ & $[12, 4]$ \\
7 & $-$ & Pop $4, 12$; Evaluate $12 - 4 = 8$; Push $8$ & $[8]$ \\
\bottomrule
\end{tabularx}
\end{table}

The evaluation completes with a single final value $8$ remaining on top of the stack.

\section{Nonlinear Structures: Binary Search Trees}

Linear data structures require linear search time $O(n)$ for unsorted data. Hierarchical structures optimize search, insertion, and deletion times through branched structural paths.

\subsection{Binary Search Tree Property}

A **binary search tree** (BST) is a hierarchical, node-based tree structure. Each node contains a key, a satellite payload, a left reference pointer, and a right reference pointer. A binary tree satisfies the binary search tree property if for every node $N$:
\begin{itemize}
    \item Every node key in the left subtree of $N$ is strictly less than $N$'s key.
    \item Every node key in the right subtree of $N$ is strictly greater than $N$'s key.
\end{itemize}

\begin{verbatim}
Binary Search Tree Layout:

       50
      /  \
    30    70
   /  \     \
  20  40    80
\end{verbatim}

\subsection{Core Operations and Algorithms}

\subsubsection{Search and Insertion}
Searching begins at the root node. The search key is compared against the current node key:
\begin{itemize}
    \item If equal, the node is returned.
    \item If the search key is smaller, search recursively continues into the left child subtree.
    \item If the search key is larger, search recursively continues into the right child subtree.
\end{itemize}
Insertion follows the same structural navigation path until reaching a \texttt{null} link, where the new node is attached as a leaf node.

\subsubsection{Deletion}
Tree node deletion must preserve the BST ordering invariant across three possible node configuration cases:
\begin{enumerate}
    \item \textbf{Node has no children (Leaf Node)}: Remove the node directly by setting its parent reference to \texttt{null}.
    \item \textbf{Node has one child}: Replace the target node with its single child by pointing the target node's parent directly to that child.
    \item \textbf{Node has two children}: Locate the node's **in-order successor** (the node with the smallest key in its right subtree). Copy the in-order successor's key and satellite payload into the target node, then recursively delete the in-order successor node from its original position (which is guaranteed to fall under Case 1 or Case 2).
\end{enumerate}

\begin{verbatim}
Deletion of Node with Two Children (Deleting Node 30):

       50                     50
      /  \                   /  \
    30    70   =====>      40    70
   /  \     \             /        \
  20  40    80           20        80
\end{verbatim}

\subsection{Tree Traversals}

Tree traversal algorithms visit every node in a tree systematically in $O(n)$ time:
\begin{itemize}
    \item \textbf{In-Order Traversal (Left, Node, Right)}: Recursively visits the left subtree, processes the current node, and visits the right subtree. On a BST, this outputs keys in ascending sorted order.
    \item \textbf{Pre-Order Traversal (Node, Left, Right)}: Processes the current node before visiting its subtrees. Used to clone or serialize tree topologies.
    \item \textbf{Post-Order Traversal (Left, Right, Node)}: Processes both subtrees prior to evaluating the current node. Used in bottom-up memory deallocation and mathematical syntax tree evaluation.
\end{itemize}

\begin{verbatim}
Tree Traversal Example:

       F
      / \
     B   G
    / \   \
   A   D   I

In-Order   (Left, Node, Right): A, B, D, F, G, I
Pre-Order  (Node, Left, Right): F, B, A, D, G, I
Post-Order (Left, Right, Node): A, D, B, I, G, F
\end{verbatim}

\section{Associative Mapping: Hash Tables}

A **hash table** is an associative data structure designed to provide constant average-time $O(1)$ key search, insertion, and deletion. It maps keys to array index locations using a mathematical transformation called a hash function.

\subsection{Hash Functions and Collisions}

A hash function $h(k)$ maps an arbitrary key space $k$ to a bounded integer range $[0, M-1]$, where $M$ is the size of the underlying array table. A uniform hash function distributes keys evenly across all array indices to minimize collisions.

A **hash collision** occurs when two distinct keys evaluate to identical indices ($h(k_1) = h(k_2)$ for $k_1 \neq k_2$). Because key spaces are typically much larger than array size $M$, collisions are unavoidable due to the Pigeonhole Principle.

\subsection{Collision Resolution Techniques}

\subsubsection{Separate Chaining}
In separate chaining, each array slot acts as a reference to an independent linked list (or bucket) storing all key-value entries mapped to that index.

\begin{verbatim}
Separate Chaining Layout:

 Slot
+---+
| 0 | --> [ Null ]
+---+
| 1 | --> [ KeyA | ValA ] ---> [ KeyB | ValB ] ---> Null
+---+
| 2 | --> [ Null ]
+---+
\end{verbatim}

Search time in a chained table depends on the average list length, governed by the **load factor** $\alpha = n / M$, where $n$ is the total number of inserted keys and $M$ is table capacity.

\subsubsection{Open Addressing}
Open addressing stores all entries directly inside the primary array. When a collision occurs, the algorithm systematically probes alternate slots until an empty cell is found:
\begin{itemize}
    \item \textbf{Linear Probing}: Inspects sequential slots using index formula $h(k, i) = (h'(k) + i) \pmod M$ for probe step $i \in \{0, 1, \dots, M-1\}$. This approach can lead to primary clustering, where contiguous blocks of occupied slots build up and slow down lookups.
    \item \textbf{Quadratic Probing}: Uses a non-linear quadratic offset $h(k, i) = (h'(k) + c_1 i + c_2 i^2) \pmod M$ to reduce primary clustering.
    \item \textbf{Double Hashing}: Uses a secondary independent hash function $h_2(k)$ to calculate probe step sizes: $h(k, i) = (h_1(k) + i \cdot h_2(k)) \pmod M$.
\end{itemize}

\subsection{Worked Example: Collision Resolution in Hash Tables}

Insert integer keys $[15, 22, 8, 29]$ into a hash table of size $M = 7$ using hash function $h(k) = k \pmod 7$.

\begin{itemize}
    \item Insert $15$: $h(15) = 15 \pmod 7 = 1$. Slot $1$ is empty. Place $15$ at index $1$.
    \item Insert $22$: $h(22) = 22 \pmod 7 = 1$. Collision at slot $1$.
    \item Insert $8$: $h(8) = 8 \pmod 7 = 1$. Collision at slot $1$.
    \item Insert $29$: $h(29) = 29 \pmod 7 = 1$. Collision at slot $1$.
\end{itemize}

Using **Linear Probing**:
\begin{enumerate}
    \item Key $15$ goes to slot $1$.
    \item Key $22$ hashes to $1$ (occupied). Probe index $(1+1) \pmod 7 = 2$. Place $22$ at slot $2$.
    \item Key $8$ hashes to $1$ (occupied). Probe index $2$ (occupied). Probe index $(1+2) \pmod 7 = 3$. Place $8$ at slot $3$.
    \item Key $29$ hashes to $1$ (occupied). Probe index $2$ (occupied), index $3$ (occupied), index $(1+3) \pmod 7 = 4$. Place $29$ at slot $4$.
\end{enumerate}

\begin{verbatim}
Linear Probing Result Table:
Index:   0      1      2      3      4      5      6
      +------+------+------+------+------+------+------+
Keys: | Null |  15  |  22  |  8   |  29  | Null | Null |
      +------+------+------+------+------+------+------+
\end{verbatim}

Using **Separate Chaining**:
\begin{verbatim}
Separate Chaining Result Table:
Index 1: [ 15 ] ---> [ 22 ] ---> [ 8 ] ---> [ 29 ] ---> Null
\end{verbatim}

\section{Comparative Analysis and Systemic Applications}

Selecting the right data structure requires evaluating operational performance, memory overhead, and implementation trade-offs.

\begin{table}[h!]
\centering
\caption{Algorithmic Time and Space Complexity Comparison}
\label{tab:complexity_comparison}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.8cm} X X X X}
\toprule
\textbf{Data Structure} & \textbf{Average Access} & \textbf{Average Search} & \textbf{Average Insertion} & \textbf{Average Deletion} \\
\midrule
Singly Linked List & $\Theta(n)$ & $\Theta(n)$ & $\Theta(1)^*$ & $\Theta(1)^*$ \\
Doubly Linked List & $\Theta(n)$ & $\Theta(n)$ & $\Theta(1)^*$ & $\Theta(1)^*$ \\
Stack (Array/List) & $\Theta(n)$ & $\Theta(n)$ & $\Theta(1)$ & $\Theta(1)$ \\
Queue (Array/List) & $\Theta(n)$ & $\Theta(n)$ & $\Theta(1)$ & $\Theta(1)$ \\
Binary Search Tree & $\Theta(\log n)$ & $\Theta(\log n)$ & $\Theta(\log n)$ & $\Theta(\log n)$ \\
Hash Table & N/A & $\Theta(1)$ & $\Theta(1)$ & $\Theta(1)$ \\
\bottomrule
\end{tabularx}
\end{table}

\noindent{\small $^*$Note: Insertion and deletion operations for linked lists run in $O(1)$ time given a direct pointer reference to the target position; otherwise, locating the position requires $O(n)$ search time.}

\subsection{Integrated Software Applications}

Real-world applications combine these core structures to manage operational tasks efficiently:
\begin{itemize}
    \item \textbf{Text Editor Undo/Redo System}: Dual stack structures store operational state histories. Undoing an action pops state data from the undo stack and pushes it onto the redo stack.
    \item \textbf{Task Scheduling and Breadth-First Search (BFS)}: Operating system process managers and graph traversal algorithms use queues to maintain execution order and process nodes sequentially.
    \item \textbf{Database Indexing and Symbol Tables}: Compilers use hash tables for constant-time lookup in scope symbol tables, while binary search trees support range queries and sorted index scans.
\end{itemize}

\section{Conclusion}

Concrete data structure implementations determine how efficient a program is in terms of speed and memory usage. Pointer-based structures manage dynamic memory allocation flexibly, restricted linear structures enforce strict access rules, hierarchical trees optimize ordered searching, and hash functions enable constant-time data retrieval. Understanding these internal mechanics provides the foundation for the next chapter, which covers choosing and tailoring the right data structure to solve complex, real-world problems.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Compare the operational time complexity and memory layouts of dynamic arrays and singly linked lists. Identify scenarios where each structure is preferred over the other.
    
    \item Trace the following operations on an initially empty stack: \texttt{push(12)}, \texttt{push(7)}, \texttt{pop()}, \texttt{push(19)}, \texttt{push(3)}, \texttt{pop()}, \texttt{peek()}. Draw the stack layout at each step and state the value returned by the final \texttt{peek()} operation.
    
    \item Explain why a standard array implementation of a queue can result in an $O(n)$ dequeue runtime performance. Show how a circular array structure resolves this issue using modular arithmetic.
    
    \item Evaluate the following postfix expression step-by-step using a stack, showing the stack state after reading each token:
    $$8 \quad 4 \quad 2 \quad / \quad * \quad 3 \quad + \quad 5 \quad -$$
    
    \item Given an unweighted binary search tree containing keys $[50, 25, 75, 10, 30, 60, 80]$, construct the resulting tree topology. Demonstrate step-by-step node updates when deleting key $25$.
    
    \item Insert keys $[18, 26, 35, 9, 44, 27]$ into a hash table of size $M = 7$ using hash function $h(k) = k \pmod 7$. Draw the resulting table structures under:
    \begin{enumerate}
        \item Linear Probing Open Addressing.
        \item Separate Chaining.
    \end{enumerate}
    
    \item A system developer uses a binary search tree to store symbol table keys. Under worst-case insertion conditions, operations degrade to $O(n)$ time. Explain why this degradation occurs and propose an architectural modification to ensure worst-case $O(\log n)$ performance.
    
    \item High-performance caching layers use a Least Recently Used (LRU) policy, which requires fast element access and fast structural updates. Identify two data structures covered in this chapter that can be combined to support $O(1)$ search and $O(1)$ displacement operations, and explain how they interact.
\end{enumerate}



# Chapter 4: choose the appropriate data structure for modelling a given problem;


Selecting the appropriate data structure is a foundational decision in software engineering. Every computational problem exhibits distinct operational access patterns, memory constraints, and structural relationships among data elements. A data structure that excels at sequential data processing may perform poorly when required to perform frequent random lookups or arbitrary insertions. Consequently, software designers must analyze problem requirements systematically to select or compose an optimal data structure rather than relying on default choices.

This chapter establishes a practical methodology for modeling computational problems and mapping their operational requirements to concrete data structures. Building on the fundamental properties of built-in data structures, abstract data types, and concrete linear and non-linear implementations studied in previous chapters, this material synthesizes operational requirements with performance trade-offs. Students will learn to analyze workloads, data relationships, and physical resource constraints to select optimal representations.

Mastering this selection framework is critical for building scalable, high-performance software systems. Inappropriate choices lead to degraded computational efficiency, excessive memory consumption, and overly complex code logic. The principles established in this chapter prepare students for formal algorithm efficiency analysis in subsequent topics, bridging conceptual software design and rigorous performance evaluation.

\section{Dimensions of Problem Requirements Analysis}

When encountering a software modeling task, the software designer must decompose the problem requirements along four primary dimensions: computational operations, structural relationships, ordering constraints, and hardware resource limits.

\subsection{Workload and Operational Patterns}
Computational workloads differ based on the frequency and performance sensitivity of core operations:
\begin{itemize}
    \item \textbf{Access and Search:} Does the problem require looking up elements by integer index, searching for specific data values, or retrieving records via unique alphanumeric keys?
    \item \textbf{Insertion and Deletion:} Are elements added or removed primarily at fixed boundaries (such as the start or end of a sequence) or at arbitrary interior locations?
    \item \textbf{Read-to-Write Ratio:} Is the workload read-heavy (dominated by search and traversal operations) or write-heavy (dominated by frequent state updates and structural modifications)?
\end{itemize}

\subsection{Data Relationships and Structural Topology}
Data elements possess inherent structural relationships that dictate the logical container topology:
\begin{itemize}
    \item \textbf{Linear Relationships:} Elements exist in a strict sequential order, where each element except boundary nodes has a single predecessor and successor.
    \item \textbf{Hierarchical Relationships:} Elements exhibit parent-child dependencies, forming tree structures where a single root node branches into subtrees.
    \item \textbf{Associative Relationships:} Data is defined by key-value bindings, where lookup operations rely on abstract keys rather than physical positions.
    \item \textbf{Set Relationships:} Elements represent unordered collections of unique items, where set membership verification and mathematical set operations dominate.
\end{itemize}

\subsection{Ordering and Uniqueness Constraints}
Constraints on data ordering and duplication narrow the set of viable candidate data structures:
\begin{itemize}
    \item \textbf{Insertion Order Preservation:} The collection must retain the exact sequence in which items were inserted into the system.
    \item \textbf{Sorted Order Maintenance:} Elements must remain continuously sorted according to a defined total ordering relation.
    \item \textbf{Uniqueness Constraints:} Duplicate values are strictly prohibited, requiring efficient membership testing during insertion.
\end{itemize}

\subsection{Resource Constraints and Physical Hardware Characteristics}
Resource limits frequently override theoretical operational efficiency considerations:
\begin{itemize}
    \item \textbf{Memory Footprint and Pointer Overhead:} Node-based structures like a singly linked list or a binary search tree store memory references alongside payload data. In contrast, dynamic arrays store elements contiguously without pointer overhead.
    \item \textbf{Cache Locality:} Modern CPUs fetch memory into hardware caches in contiguous blocks. The spatial proximity of data elements in memory, known as \textbf{cache locality}, enables arrays to execute significantly faster than pointer-based structures whose nodes are scattered across heap memory (Figure~\ref{fig:memory_layout}).
    \item \textbf{Allocation Predictability:} Dynamic reallocation strategies incur latency spikes when resizing. Fixed-size applications favor pre-allocated contiguous memory blocks.
\end{itemize}

\begin{figure}[htbp]
\centering
\begin{verbatim}
Contiguous Memory Layout (Dynamic Array):
+---------+---------+---------+---------+---------+
| Data[0] | Data[1] | Data[2] | Data[3] | Data[4] |  <-- Loaded in single
+---------+---------+---------+---------+---------+      cache line
Addr: 0x1000  0x1004    0x1008    0x100C    0x1010

Pointer-Based Node Layout (Linked List):
+---------+------+      +---------+------+      +---------+------+
| Data[0] | Next |----> | Data[1] | Next |----> | Data[2] | Null |
+---------+------+      +---------+------+      +---------+------+
Addr: 0x1000           Addr: 0x4800           Addr: 0x2200
                       (Heap Allocation Scatter -> Cache Misses)
\end{verbatim}
\caption{Comparison of Contiguous Array Memory Layout and Pointer-Based Node Layout.}
\label{fig:memory_layout}
\end{figure}

The initial mapping from problem characteristics to candidate data structures is summarized in Figure~\ref{fig:selection_flowchart}.

\begin{figure}[htbp]
\begin{verbatim}
                         +------------------------+
                         |  Analyze Problem Requirements  |
                         +-----------+------------+
                                     |
                                     v
                       /----------------------------\
                      / What is the Primary Relationship? \
                     \------------------------------/
                      /       |            |        \
            Key-Value/        |Hierarchical|         \Sequential / Linear
                    /         |            |          \
                   v          v            v           v
            +------------+ +--------+ +----------+ +---------------+
            | Hash Table | | Binary | | Priority | | Array / List  |
            | / Dictionary| | Search | | Queue /  | | Stack / Queue |
            |            | | Tree   | | Heap     | |               |
            +------------+ +--------+ +----------+ +---------------+
                   |          |            |           |
                   v          v            v           v
            Lookup by     Ordered      Priority-    Position-based
            Unique Key    Range Search  Retrieval    Access / LIFO / FIFO
\end{verbatim}

\caption{Taxonomy of Problem Requirements and Candidate Data Structures.}
\label{fig:selection_flowchart}
\end{figure}

\section{Comparative Analysis of Core Data Structures}

Selecting an optimal data structure requires balancing execution time against spatial overhead. This fundamental compromise is known as the \textbf{time-space trade-off}, where an algorithm or data structure achieves faster operation execution by consuming additional memory, or conversely minimizes memory consumption at the expense of runtime performance.

For example, a hash table provides near-instantaneous search by reserving extra unallocated space in an underlying bucket array. Conversely, an unsorted dynamic array consumes minimal memory overhead but requires scanning every element sequentially to perform a search.

Table~\ref{tab:ds_comparison} provides a comparative reference of operational characteristics and memory profiles across standard linear and non-linear data structures.

\begin{table}[htbp]
\centering
\caption{Operational Complexity and Resource Profiles of Core Data Structures}
\label{tab:ds_comparison}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.5cm} X X X >{\raggedright\arraybackslash}p{2.8cm}}
\toprule
\textbf{Data Structure} & \textbf{Search / Lookup} & \textbf{Insertion} & \textbf{Deletion} & \textbf{Memory Overhead \& Locality} \\
\midrule
\textbf{Array} & $O(1)$ by index; $O(n)$ by value & $O(n)$ arbitrary position & $O(n)$ arbitrary position & Zero pointer overhead; high cache locality. \\
\midrule
\textbf{Dynamic Array} & $O(1)$ by index; $O(n)$ by value & $O(1)$ amortized at end; $O(n)$ arbitrary & $O(1)$ at end; $O(n)$ arbitrary & Low memory overhead; high cache locality. \\
\midrule
\textbf{Singly Linked List} & $O(n)$ by index or value & $O(1)$ at head; $O(n)$ arbitrary & $O(1)$ at head; $O(n)$ arbitrary & One pointer reference per node; poor cache locality. \\
\midrule
\textbf{Doubly Linked List} & $O(n)$ by index or value & $O(1)$ at ends; $O(1)$ given node reference & $O(1)$ at ends; $O(1)$ given node reference & Two pointer references per node; poor cache locality. \\
\midrule
\textbf{Stack} & $O(n)$ general search & $O(1)$ push operation & $O(1)$ pop operation & Dependent on backing dynamic array or list container. \\
\midrule
\textbf{Queue} & $O(n)$ general search & $O(1)$ enqueue operation & $O(1)$ dequeue operation & Dependent on backing ring buffer or list container. \\
\midrule
\textbf{Hash Table / Dictionary} & $O(1)$ average time by key & $O(1)$ average time & $O(1)$ average time & Hash bucket capacity overhead; poor sequential locality. \\
\midrule
\textbf{Binary Search Tree} & $O(\log n)$ average search & $O(\log n)$ average insertion & $O(\log n)$ average deletion & Two pointer references per node; supports sorted order. \\
\bottomrule
\end{tabularx}
\end{table}

\section{Systematic Selection Methodology}

To evaluate software requirements methodically, software developers follow a structured four-stage selection framework, illustrated in Figure~\ref{fig:selection_pipeline}.

\begin{figure}[htbp]
\begin{verbatim}
+-----------------------------------------------------------------+
| Stage 1: Identify Key Data Relationships                        |
|   - Associative Key-Value  ---> Hash Table / Dictionary         |
|   - Hierarchical / Parent  ---> Binary Search Tree              |
|   - Set Membership         ---> Set                             |
|   - Linear / Sequential    ---> Proceed to Stage 2              |
+-----------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------+
| Stage 2: Evaluate Dominant Access Protocols                     |
|   - Direct Index Access    ---> Array / Dynamic Array           |
|   - LIFO (Stack) Protocol  ---> Stack                           |
|   - FIFO (Queue) Protocol  ---> Queue                           |
|   - Highest Priority First ---> Priority Queue                  |
|   - Interior Arbitrary Mod ---> Linked List / Tree              |
+-----------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------+
| Stage 3: Apply Order and Uniqueness Rules                       |
|   - Mandatory Sorting      ---> Binary Search Tree / Sorted Array |
|   - Unique Keys Required   ---> Set / Hash Table                |
+-----------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------+
| Stage 4: Factor Hardware and Memory Constraints                 |
|   - Maximize Cache Speeds  ---> Contiguous Memory (Dynamic Array)|
|   - Fixed Memory Allocation---> Static Array                    |
+-----------------------------------------------------------------+
\end{verbatim}
\caption{Four-Stage Decision Pipeline for Data Structure Selection.}
\label{fig:selection_pipeline}
\end{figure}

The evaluation steps are executed in order:
\begin{enumerate}
    \item \textbf{Identify Data Relationships:} Determine if data elements are bound by keys, hierarchical structures, set definitions, or simple sequences.
    \item \textbf{Evaluate Operational Workloads:} Identify the most frequent operations (such as insertions, deletions, or searches) and choose structures optimized for those primary access protocols.
    \item \textbf{Apply Constraints:} Determine whether elements must remain strictly ordered or unique across the collection lifecycle.
    \item \textbf{Assess Memory Overhead and Hardware Targets:} Factor in pointer allocation costs, cache locality requirements, and device memory limitations.
\end{enumerate}

\section{Worked Problem Modelling Scenarios}

The following real-world software engineering scenarios demonstrate how to apply the systematic selection methodology to choose optimal data structures.

\subsection{Scenario 1: Undo and Redo Subsystem for a Text Editor}

\textbf{Problem Specification:} A text editor application requires an internal system to track user modifications, enabling unlimited undo and redo operations.

\textbf{Requirement Analysis:}
\begin{itemize}
    \item Modifying text pushes a new state snapshot to the undo history.
    \item Performing an undo operation reverts the most recent modification, pushing the reverted state to a redo history.
    \item Access follows a strict Last-In, First-Out (LIFO) protocol. Access to intermediate historical states is not required.
\end{itemize}

\textbf{Candidate Evaluation:}
\begin{itemize}
    \item \textbf{Dynamic Array / Stack:} Provides $O(1)$ push and pop operations at the boundary. Dynamic arrays store snapshots contiguously, maximizing memory access speed and eliminating pointer overhead.
    \item \textbf{Doubly Linked List:} Supports $O(1)$ boundary insertions and removals, but incurs pointer allocation overhead for every recorded edit operation.
\end{itemize}

\textbf{Selection and Justification:} A \textbf{stack} abstract data type implemented via a dynamic array is optimal. It offers $O(1)$ operational execution speed for LIFO access while minimizing memory overhead and leveraging processor cache locality.

\subsection{Scenario 2: Real-time Operating System Task Scheduler}

\textbf{Problem Specification:} An operating system scheduler manages active execution threads. Processes arrive dynamically with associated priority values. The system must continuously identify and extract the waiting process with the highest priority score.

\textbf{Requirement Analysis:}
\begin{itemize}
    \item Dynamic task insertions occur continuously.
    \item Retrieval must always return the item with the highest priority score, rather than the oldest arrival.
    \item Linear searches across unsorted collections are unacceptable due to strict latency bounds.
\end{itemize}

\textbf{Candidate Evaluation:}
\begin{itemize}
    \item \textbf{Unsorted Dynamic Array:} Insertions execute in $O(1)$ time, but locating the highest priority process requires scanning every element ($O(n)$ time complexity).
    \item \textbf{Sorted Array:} Locating and removing the highest priority item takes $O(1)$ time at the array boundary, but inserting new tasks requires shifting elements ($O(n)$ time complexity).
    \item \textbf{Priority Queue:} A \textbf{priority queue} abstract data type implemented via a heap or binary tree structure provides $O(\log n)$ insertion time and $O(\log n)$ priority extraction time.
\end{itemize}

\textbf{Selection and Justification:} A priority queue is chosen because it balances dynamic insertions and removals in logarithmic time, ensuring predictable performance under high workload concurrency.

\subsection{Scenario 3: Academic Record Database with Range Queries}

\textbf{Problem Specification:} A university administration portal stores student academic records identified by a unique Matriculation Number. The system requires constant-time lookups by student ID and must frequently produce ordered reports for ranges of Matriculation Numbers (for example, generating a roster for student IDs between 1000 and 2000).

\textbf{Requirement Analysis:}
\begin{itemize}
    \item Exact key lookups must execute rapidly.
    \item Range queries require traversing data elements in sorted order within specified lower and upper bounds.
\end{itemize}

\textbf{Candidate Evaluation:}
\begin{itemize}
    \item \textbf{Hash Table / Dictionary:} Delivers $O(1)$ average search time for individual key lookups. However, hash functions scatter keys unpredictably, making range queries inefficient ($O(n)$ full table scan).
    \item \textbf{Binary Search Tree:} Provides $O(\log n)$ search performance and maintains elements in sorted order, enabling efficient range traversals in $O(\log n + k)$ time, where $k$ is the number of elements in the target range.
    \item \textbf{Hybrid Dual-Structure (Hash Table + Binary Search Tree):} Combines a hash table for $O(1)$ point lookups with a binary search tree for range queries, using duplicate references pointing to shared record memory.
\end{itemize}

\textbf{Selection and Justification:} If range queries occur frequently alongside single-record lookups, a \textbf{binary search tree} provides an excellent single-container solution. If single-item lookups heavily dominate the workload, a hybrid container system combining a hash table and a binary search tree offers the best overall performance, trading extra reference memory to achieve optimal lookup speeds.

\section{Conclusion}

Selecting the correct data structure requires a structured evaluation of operational access patterns, data relationships, ordering rules, and hardware limits. As demonstrated by the modeling scenarios, no single data structure performs optimally across all computational contexts. Software engineering requires evaluating operational trade-offs to select or combine data structures effectively.

While this chapter established qualitative selection criteria, evaluating algorithm scalability quantitatively requires formal mathematical models. The next chapter introduces \textbf{big-O notation} and formal algorithm analysis, providing the mathematical tools necessary to calculate upper bounds on execution time and memory usage across data structure operations.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Compare dynamic arrays and doubly linked lists for a software module requiring frequent insertions in the middle of a collection versus one requiring end-only additions. Identify which structure is preferred in each case and explain your reasoning.
    \item A developer chooses a hash table to implement a gaming leaderboard that must print the top ten highest scores in sorted order every second. Identify the primary structural limitation of hash tables in this scenario, and propose an alternative data structure that solves the problem efficiently.
    \item Define the concept of cache locality and explain how memory layout influences the practical performance of contiguous arrays compared to pointer-based linked lists on modern processors.
    \item A hospital triage system manages arriving emergency room patients based on assigned severity scores. Patients with higher severity scores must be treated before patients with lower scores, regardless of arrival time. Identify the most appropriate abstract data type for this system and justify your choice over a standard FIFO queue.
    \item Consider a system workload consisting of 99\% search operations and 1\% insertion operations on a static dataset. Evaluate whether a sorted array or a binary search tree is more appropriate, factoring in execution time and memory footprint.
    \item A system requires storing string key-value pairs on an embedded device with severely limited memory. Explain the time-space trade-off involved when deciding between a hash table and a sorted array of key-value tuples.
    \item Design a hybrid data structure for an online shopping cart application that must support $O(1)$ item lookup by Product ID, preserve the chronological insertion sequence of added items, and allow fast deletion of items from any position in the cart. Explain how the individual data structures interact within your design.
\end{enumerate}



# Chapter 5: analyse simple algorithms and determine their efficiency using big-O notation; and


Selecting an appropriate data structure requires a mathematical framework to evaluate algorithmic efficiency independently of physical execution hardware. Measuring wall-clock runtime on a specific computer introduces confounding factors such as CPU clock frequency, compiler flags, operating system scheduling, and hardware cache structures. Algorithm analysis circumvents these empirical variables by expressing execution time and memory consumption as mathematical functions of the input size $n$.

This chapter establishes the principles of **asymptotic analysis**, focusing on mathematical notations used to bound performance as problem size grows toward infinity. It introduces formal definitions for **big-O notation**, Big-$\Omega$ notation, and Big-$\Theta$ notation. The chapter examines best-case, worst-case, and average-case analysis scenarios, and details formal step-counting techniques for analyzing iterative loops and simple recursive operations.

Mastering efficiency analysis enables computer scientists to predict how software implementations scale long before deployment. This mathematical grounding directly links the linear lists, trees, and hash tables examined in prior chapters to real-world application domains, laying the groundwork for analyzing complex algorithms such as **data compression** protocols in subsequent topics.

\section{Principles of Algorithm Efficiency}

Evaluating an algorithm requires measuring how its resource requirements scale as the size of the input $n$ increases. The primary resources under evaluation are execution time (time complexity) and memory consumption (space complexity). Rather than measuring execution time in seconds, algorithm analysis counts primitive operations. A primitive operation is a low-level computation whose execution time is bounded by a constant, regardless of input size.

Examples of primitive operations include:
\begin{itemize}
    \item Assigning a value to a variable.
    \item Performing a basic arithmetic operation (addition, subtraction, multiplication).
    \item Comparing two numerical values.
    \item Indexing into an **array** or dereferencing a memory reference.
    \item Returning a value from a function.
\end{itemize}

Let $T(n)$ represent the exact total count of primitive operations performed by an algorithm for an input of size $n$. For large values of $n$, low-order terms and constant coefficients exert negligible influence on the overall growth rate of $T(n)$. Asymptotic analysis focuses on the dominant term of $T(n)$ as $n$ approaches infinity, isolating the underlying efficiency class of the algorithm.

\section{Formal Asymptotic Notations}

Asymptotic notation provides a mathematical language for bounding functions. Three primary notations are used to classify algorithm resource consumption: Big-O, Big-$\Omega$, and Big-$\Theta$.

\subsection{Big-O Notation (Upper Bound)}

**Big-O notation** defines an asymptotic upper bound on a function. It characterizes the mathematical ceiling of an algorithm's growth rate, ensuring that resource usage will not exceed a specific growth rate for sufficiently large inputs.

Formally, given two non-negative functions $f(n)$ and $g(n)$, $f(n) \in O(g(n))$ if there exist positive constants $c > 0$ and $n_0 \ge 1$ such that:
$$f(n) \le c \cdot g(n) \quad \text{for all } n \ge n_0$$

To establish that $f(n) = 3n^2 + 5n + 8$ is $O(n^2)$, appropriate constants $c$ and $n_0$ must be identified. Observing that for all $n \ge 1$:
$$5n \le 5n^2 \quad \text{and} \quad 8 \le 8n^2$$
Adding these inequalities yields:
$$3n^2 + 5n + 8 \le 3n^2 + 5n^2 + 8n^2 = 16n^2$$
Setting $c = 16$ and $n_0 = 1$ demonstrates that $f(n) \le 16n^2$ for all $n \ge 1$. Thus, $f(n) \in O(n^2)$.

\subsection{Big-$\Omega$ Notation (Lower Bound)}

Big-$\Omega$ notation defines an asymptotic lower bound on a function. It describes the minimum growth rate an algorithm guarantees for large input sizes.

Formally, $f(n) \in \Omega(g(n))$ if there exist positive constants $c > 0$ and $n_0 \ge 1$ such that:
$$f(n) \ge c \cdot g(n) \quad \text{for all } n \ge n_0$$

For the function $f(n) = 3n^2 + 5n + 8$, observing that $5n + 8 \ge 0$ for $n \ge 1$ gives:
$$3n^2 + 5n + 8 \ge 3n^2$$
Setting $c = 3$ and $n_0 = 1$ confirms that $f(n) \in \Omega(n^2)$.

\subsection{Big-$\Theta$ Notation (Tight Bound)}

Big-$\Theta$ notation defines an asymptotically tight bound. A function $f(n)$ belongs to $\Theta(g(n))$ if and only if $f(n)$ is bounded both above and below by scaled multiples of $g(n)$.

Formally, $f(n) \in \Theta(g(n))$ if there exist positive constants $c_1 > 0$, $c_2 > 0$, and $n_0 \ge 1$ such that:
$$c_1 \cdot g(n) \le f(n) \le c_2 \cdot g(n) \quad \text{for all } n \ge n_0$$

Because $f(n) = 3n^2 + 5n + 8$ is both $O(n^2)$ with $c_2 = 16$ and $\Omega(n^2)$ with $c_1 = 3$, it follows directly that $f(n) \in \Theta(n^2)$.

\begin{verbatim}
  Growth Rate / Operations
        ^
        |                                       / c_2 * g(n)  [Upper Bound]
        |                                      /
        |                                     /  / f(n)        [Algorithm Growth]
        |                                    /  /
        |                                   /  /   / c_1 * g(n)  [Lower Bound]
        |                                  /  /   /
        |                                 /  /   /
        |                                /  /   /
        |                               /  /   /
        |                              /  /   /
        |                             /  /   /
        |____________________________/__/__/__________________
        0                           n_0                     -> Input Size (n)
\end{verbatim}

\begin{table}[htbp]
\centering
\caption{Comparison of Formal Asymptotic Notations}
\label{tab:asymptotic_notations}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{4.2cm} >{\raggedright\arraybackslash}p{2.2cm} X}
\toprule
\textbf{Notation} & \textbf{Mathematical Inequality} & \textbf{Bound Type} & \textbf{Practical Interpretation} \\
\midrule
$O(g(n))$ & $f(n) \le c \cdot g(n)$ for $n \ge n_0$ & Upper bound & Worst-case growth rate ceiling. Resource usage will not exceed this rate. \\
$\Omega(g(n))$ & $f(n) \ge c \cdot g(n)$ for $n \ge n_0$ & Lower bound & Best-case growth rate floor. Resource usage will not drop below this rate. \\
$\Theta(g(n))$ & $c_1 \cdot g(n) \le f(n) \le c_2 \cdot g(n)$ for $n \ge n_0$ & Tight bound & Exact growth rate matching $g(n)$ within constant factor bounds. \\
\bottomrule
\end{tabularx}
\end{table}

\section{Analysis Scenarios: Worst-Case, Best-Case, and Average-Case}

An algorithm's runtime can vary significantly based on the specific arrangement of input elements, even when input size $n$ remains constant. Three performance scenarios are evaluated:

\begin{itemize}
    \item **worst-case time complexity**: The maximum number of primitive operations performed over all valid inputs of size $n$. It provides a strict upper boundary guarantee for system safety and mission-critical design.
    \item **best-case time complexity**: The minimum number of primitive operations performed over all valid inputs of size $n$. It represents ideal conditions but rarely serves as a useful benchmark for general software performance.
    \item **average-case time complexity**: The expected number of primitive operations executed over all inputs of size $n$, weighted by their probability distribution.
\end{itemize}

Consider a linear search operation executed on an unsorted **array** containing $n$ elements. The algorithm inspects each element sequentially from index $0$ to index $n-1$ until the target element is found or the array ends.

\begin{itemize}
    \item Best-Case: The target element resides at index $0$. The algorithm completes after $1$ comparison, yielding $O(1)$ time complexity.
    \item Worst-Case: The target element is located at index $n-1$ or is entirely absent from the array. The algorithm performs $n$ comparisons, yielding $O(n)$ time complexity.
    \item Average-Case: Assuming the target is equally likely to be at any index from $0$ to $n-1$, the expected number of comparisons is calculated as:
    $$\text{Average Comparisons} = \frac{1}{n} \sum_{i=1}^{n} i = \frac{1}{n} \left( \frac{n(n+1)}{2} \right) = \frac{n+1}{2}$$
    Dropping constant factors and low-order terms establishes an average-case time complexity of $O(n)$.
\end{itemize}

\section{Common Complexity Classes and Growth Rates}

Algorithms are categorized into standard complexity classes based on their dominant growth terms. Ordering these classes from most efficient to least efficient yields:
$$O(1) < O(\log n) < O(n) < O(n \log n) < O(n^2) < O(2^n) < O(n!)$$

The relative growth rates of these complexity functions are illustrated below:

\begin{verbatim}
  Resource Usage T(n)
        ^
        |                                       / O(2^n) Exponential
        |                                      /
        |                                     /  / O(n^2) Quadratic
        |                                    /  /
        |                                   /  /   / O(n log n) Linearithmic
        |                                  /  /   /
        |                                 /  /   /   / O(n) Linear
        |                                /  /   /   /
        |                               /  /   /   /
        |                              /  /   /   /____ O(log n) Logarithmic
        |                             /  /   /   /
        |____________________________/__/__/__/________ O(1) Constant
        +----------------------------------------------------> Input Size (n)
\end{verbatim}

\begin{table}[htbp]
\centering
\caption{Comparison of Growth Classes Across Operations Count}
\label{tab:growth_classes}
\begin{tabularx}{\textwidth}{X >{\raggedright\arraybackslash}p{2cm} >{\raggedright\arraybackslash}p{2cm} >{\raggedright\arraybackslash}p{2.2cm} X}
\toprule
\textbf{Complexity Class} & \textbf{$n = 10$} & \textbf{$n = 100$} & \textbf{$n = 1,000$} & \textbf{Common Data Structure Context} \\
\midrule
$O(1)$ Constant & $1$ & $1$ & $1$ & **array** index lookup, **stack** push/pop \\
$O(\log n)$ Logarithmic & $\approx 3.3$ & $\approx 6.6$ & $\approx 10$ & **binary search tree** lookup, binary search \\
$O(n)$ Linear & $10$ & $100$ & $1,000$ & **singly linked list** traversal, linear search \\
$O(n \log n)$ Linearithmic & $\approx 33$ & $\approx 664$ & $\approx 9,966$ & Merge sort, heap operations \\
$O(n^2)$ Quadratic & $100$ & $10,000$ & $1,000,000$ & Insertion sort, nested matrix operations \\
$O(2^n)$ Exponential & $1,024$ & $1.27 \times 10^{30}$ & $1.07 \times 10^{301}$ & Exhaustive recursive search \\
\bottomrule
\end{tabularx}
\end{table}

\section{Analyzing Iterative Algorithms}

Determining the time complexity of iterative algorithms requires counting operations inside loop structures and expressing total operations as algebraic sums.

\subsection{Sequential Loops}

When code blocks execute sequentially, their individual time complexities are summed. The dominant term dictates the overall upper bound:
$$T(n) = T_1(n) + T_2(n) \implies O(\max(f_1(n), f_2(n)))$$

\subsection{Nested Loops with Independent Bounds}

When loops are nested and the inner loop bound does not depend on the outer loop counter, total operations equal the product of the iteration counts.

\begin{verbatim}
def matrix_fill(matrix, n):
    for i in range(n):          # Outer loop executes n times
        for j in range(n):      # Inner loop executes n times
            matrix[i][j] = 0    # O(1) primitive assignment
\end{verbatim}

The inner assignment runs $n$ times for each outer loop iteration. Total primitive operations equal $n \times n = n^2$. The worst-case time complexity is $O(n^2)$.

\subsection{Dependent Nested Loops}

When loop counters interact, the inner loop bounds depend on the outer loop variable. Total execution count is determined by formulating and evaluating a summation.

Consider the following triangular loop construct:

\begin{verbatim}
def print_pairs(arr, n):
    for i in range(n):             # Outer loop runs for i = 0 to n-1
        for j in range(i + 1, n):  # Inner loop runs from i + 1 to n-1
            print(arr[i], arr[j])  # Primitive O(1) operation
\end{verbatim}

Analyzing iteration counts per outer loop step:
\begin{itemize}
    \item When $i = 0$, inner loop executes $(n - 1)$ times.
    \item When $i = 1$, inner loop executes $(n - 2)$ times.
    \item When $i = n - 2$, inner loop executes $1$ time.
    \item When $i = n - 1$, inner loop executes $0$ times.
\end{itemize}

Total primitive operations are calculated by summing the arithmetic series:
$$T(n) = \sum_{i=0}^{n-1} (n - 1 - i) = (n - 1) + (n - 2) + \dots + 1 + 0 = \frac{n(n - 1)}{2} = \frac{n^2}{2} - \frac{n}{2}$$

Discarding low-order terms and constant factors reveals a time complexity of $O(n^2)$.

\subsection{Logarithmic Loops}

Loops that scale their counter variable via multiplication or division in each step yield logarithmic time complexities.

\begin{verbatim}
def divide_step(n):
    count = 0
    i = n
    while i > 1:
        count += 1
        i = i // 2  # Integer division by 2
    return count
\end{verbatim}

Let $k$ be the number of iterations executed before $i \le 1$. The variable $i$ takes the values $n, n/2, n/4, \dots, n/2^k$. The loop terminates when:
$$\frac{n}{2^k} \le 1 \implies 2^k \ge n \implies k = \lceil \log_2 n \rceil$$

Because $k$ total steps are executed, the overall time complexity is $O(\log n)$.

\section{Analyzing Recursive Algorithms}

Recursive algorithms call themselves on smaller subproblems. Analyzing their time complexity requires defining a **recurrence relation**, which expresses the overall execution time $T(n)$ in terms of $T(k)$ for smaller input sizes $k < n$.

\subsection{Expansion Method for Recurrences}

The expansion method involves repeatedly substituting a recurrence equation into itself until a recognizable pattern emerges, terminated by a base case.

Consider recursive binary search operating on a sorted array of size $n$. The algorithm evaluates the middle element and recursively searches either the left or right half:
\begin{equation}
T(n) = 
\begin{cases} 
d & \text{if } n = 1 \\ 
T(n/2) + c & \text{if } n > 1 
\end{cases}
\end{equation}
where $c$ represents the constant time taken for middle element comparisons, and $d$ represents base case execution.

Expanding $T(n)$ step by step:
$$T(n) = T(n/2) + c$$
Substituting $T(n/2) = T(n/4) + c$:
$$T(n) = (T(n/4) + c) + c = T(n/4) + 2c$$
Substituting $T(n/4) = T(n/8) + c$:
$$T(n) = (T(n/8) + c) + 2c = T(n/8) + 3c$$

After $k$ expansions, the general relation is:
$$T(n) = T(n/2^k) + k \cdot c$$

The expansion reaches the base case when $n/2^k = 1$, which occurs when $2^k = n$, or $k = \log_2 n$. Substituting $k = \log_2 n$ back into the expanded equation yields:
$$T(n) = T(1) + c \log_2 n = d + c \log_2 n$$

Removing constants and non-dominant terms yields a worst-case time complexity of $O(\log n)$.

\begin{verbatim}
                   T(n)                     Depth 0: Work = c
                  /    \
             T(n/2)    [O(1) Work]          Depth 1: Work = c
             /    \
        T(n/4)    [O(1) Work]          Depth 2: Work = c
        /    \
     ...      [O(1) Work]          ...
     /
   T(1)       [O(1) Base Work]     Depth log_2(n): Work = d

   Total Time Complexity: sum of work across all depths = O(log n)
\end{verbatim}

\section{Space Complexity and Auxiliary Memory}

Space complexity analyzes the total memory allocated by an algorithm as a function of input size $n$. Total space complexity comprises two distinct components:

\begin{itemize}
    \item Input space: Memory occupied by the original input data structure.
    \item **auxiliary space**: Temporary or additional memory allocated during execution for algorithm processing, including working **dynamic arrays**, stack memory, or extra references.
\end{itemize}

Algorithm design prioritizes minimizing auxiliary space. For instance, an in-place sorting algorithm requires $O(1)$ auxiliary space beyond the input array, whereas non-in-place algorithms require $O(n)$ auxiliary space to allocate secondary arrays.

\subsection{Call Stack Space in Recursive Algorithms}

Recursive execution consumes auxiliary memory on the system call stack. Each active function call allocates a stack frame storing local variables, parameters, and return addresses. The auxiliary space complexity of a recursive algorithm equals the maximum depth of its call stack multiplied by the memory consumed per frame.

For instance, computing a factorial iteratively requires $O(1)$ auxiliary space:

\begin{verbatim}
def iterative_factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
\end{verbatim}

In contrast, the recursive formulation allocates $n$ stack frames, generating $O(n)$ auxiliary space complexity:

\begin{verbatim}
def recursive_factorial(n):
    if n <= 1:
        return 1
    return n * recursive_factorial(n - 1)  # Max stack depth = n
\end{verbatim}

\begin{verbatim}
Iterative Call Stack (O(1) Auxiliary Space):
+-------------------------------------------------+
| iterative_factorial(n): frame reused each step  |
+-------------------------------------------------+

Recursive Call Stack (O(n) Auxiliary Space):
+-------------------------------------------------+
| recursive_factorial(1)   [Depth n: Base Case]   |
+-------------------------------------------------+
| ...                                             |
+-------------------------------------------------+
| recursive_factorial(n-1) [Depth 2]              |
+-------------------------------------------------+
| recursive_factorial(n)   [Depth 1: Initial Call]  |
+-------------------------------------------------+
\end{verbatim}

\begin{table}[htbp]
\centering
\caption{Space Complexity Trade-offs Across Common Data Structure Operations}
\label{tab:space_complexity}
\begin{tabularx}{\textwidth}{X >{\raggedright\arraybackslash}p{3cm} >{\raggedright\arraybackslash}p{3cm} X}
\toprule
\textbf{Data Structure / Operation} & \textbf{Time Complexity} & \textbf{Auxiliary Space} & \textbf{Primary Source of Space Usage} \\
\midrule
Array Indexing & $O(1)$ & $O(1)$ & Direct offset calculation \\
Linked List Traversal & $O(n)$ & $O(1)$ & Single pointer reference tracking \\
Recursion on Balanced Tree & $O(\log n)$ & $O(\log n)$ & Function call stack depth \\
Recursion on Unbalanced Tree & $O(n)$ & $O(n)$ & Degenerate call stack depth \\
**hash table** Lookup & $O(1)$ average & $O(n)$ total & Hash buckets and entry arrays \\
\bottomrule
\end{tabularx}
\end{table}

Evaluating both time complexity and space complexity reveals essential **time-space trade-off** principles. Choosing an optimal algorithm involves balancing the computational speed of time execution against the physical memory limits imposed by auxiliary space allocation.

\section{Conclusion}

Asymptotic analysis provides the mathematical framework for measuring algorithm performance across scaling input sizes. By classifying operations into time and space complexity bounds such as Big-O, Big-$\Omega$, and Big-$\Theta$, developers can rigorously evaluate algorithmic performance independently of underlying physical hardware. Understanding these analysis methods enables precise comparative evaluations across fundamental data structures.

This efficiency analysis framework serves as a core decision tool when selecting and constructing data structures for specialized software applications. The mathematical tools established in this chapter will be applied directly to evaluate domain-specific operations in the next chapter, which explores application domains such as **data compression**, graph indexing, and dynamic memory management.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Explain why measuring the wall-clock execution time of an algorithm on a physical machine is insufficient for determining algorithm efficiency. Identify three machine-dependent factors that distort empirical measurements.
    \item Formal mathematical definitions specify upper, lower, and tight performance bounds.
    \begin{enumerate}
        \item State the formal mathematical definition of Big-O notation.
        \item Using the formal definition, prove that $f(n) = 7n^2 + 11n + 5$ is $O(n^2)$ by selecting valid positive constants $c$ and $n_0$.
    \end{enumerate}
    \item Compare worst-case, best-case, and average-case time complexities using linear search on an array of size $n$ as an example. Explain why worst-case time complexity is preferred for real-time safety systems.
    \item Analyze the worst-case time complexity of the following code fragment by performing exact operation step counting:
\begin{verbatim}
def execute_loops(n):
    total = 0
    for i in range(n):
        j = 1
        while j < n:
            total += arr[i] + j
            j = j * 2
    return total
\end{verbatim}
    \item A recursive algorithm produces the recurrence relation $T(n) = T(n - 1) + c$ for $n > 1$, with base case $T(1) = d$. 
    \begin{enumerate}
        \item Use the expansion method to solve for the closed-form complexity of $T(n)$.
        \item Identify an operation on a linear data structure that exhibits this recurrence pattern.
    \end{enumerate}
    \item Explain the distinction between total space complexity and auxiliary space complexity. Describe a scenario where an iterative algorithm and a recursive algorithm perform identical computations with the same time complexity but different auxiliary space complexities.
    \item A developer must choose between two algorithms for processing a dataset of $n$ elements: Algorithm A has a time complexity of $O(n^2)$ with $O(1)$ auxiliary space, while Algorithm B has a time complexity of $O(n \log n)$ with $O(n)$ auxiliary space. Explain how dataset scale and hardware memory constraints should guide the selection of the appropriate algorithm.
\end{enumerate}



# Chapter 6: apply the knowledge of data structures to other application domains like data compression


Data structures serve as foundational building blocks across computer systems. While basic implementations demonstrate individual operations such as insertion, deletion, and traversal, practical software applications demand composite configurations. Real-world engineering domains, including data compression, high-performance caching, database search engines, and network routing, rely on combining elementary structures into specialized software architectures.

Data compression algorithms reduce storage overhead and network bandwidth requirements by reorganizing data using specialized tree structures and priority queues. Memory management subsystems maintain real-time execution speeds through composite cache structures that pair key lookup tables with ordering lists. Search engines and network routers utilize specialized search trees and graph representations to evaluate millions of queries and routing decisions per second.

This chapter applies foundational data structures to solve algorithmic problems across system domains. By examining these implementations in context, this chapter demonstrates the practical application of asymptotic optimization, structural trade-offs, and object design principles introduced throughout this course.

\section{Data Compression via Optimal Prefix Trees}

Data compression is the process of encoding information using fewer bits than the original representation. Lossless data compression guarantees that the original data can be perfectly reconstructed from the compressed representation. A fundamental approach to lossless compression relies on variable-length character encoding, where frequently occurring characters are assigned shorter bit sequences, while rarer characters receive longer bit sequences.

To ensure unambiguous decoding, variable-length codes must satisfy the prefix property. A \textbf{prefix code} is a coding system in which no valid code word is a prefix of any other valid code word. This property allows a continuous stream of compressed bits to be parsed sequentially without delimiter tokens.

\subsection{Huffman Coding Algorithm}

\textbf{Huffman coding} is an algorithmic method for constructing optimal prefix codes. The algorithm uses a min-heap priority queue to build a full binary tree bottom-up, based on the relative frequencies of input symbols.

The tree construction procedure follows a deterministic sequence:
\begin{enumerate}
    \item Compute the occurrence frequency of each unique symbol in the input source.
    \item Create a leaf node for each symbol and insert all leaf nodes into a min-heap priority queue ordered by frequency.
    \item While the priority queue contains more than one node:
    \begin{enumerate}
        \item Extract the two nodes with the lowest frequencies ($q_1$ and $q_2$).
        \item Create a new internal node with a frequency equal to the sum of $q_1$ and $q_2$.
        \item Set $q_1$ as the left child and $q_2$ as the right child of the internal node.
        \item Insert the new internal node back into the min-heap.
    \end{enumerate}
    \item The remaining single node in the priority queue represents the root of the complete Huffman tree.
\end{enumerate}

Traversing the resulting binary tree assigns binary digits to edges: left branches represent bit $0$ and right branches represent bit $1$. The binary string accumulated from the root to a leaf node forms the unique variable-length prefix code for that symbol.

\subsection{Worked Example: Encoding "ABRACADABRA"}

Consider compressing the 11-character string \texttt{"ABRACADABRA"}. Standard fixed-length ASCII encoding allocates 8 bits per character, requiring $11 \times 8 = 88$ bits.

First, tally character frequencies:
\begin{table}[htbp]
\centering
\caption{Symbol Frequency Table for "ABRACADABRA"}
\begin{tabularx}{0.6\textwidth}{>{\centering\arraybackslash}X >{\centering\arraybackslash}X}
\toprule
\textbf{Symbol} & \textbf{Frequency} \\
\midrule
A & 5 \\
B & 2 \\
R & 2 \\
C & 1 \\
D & 1 \\
\bottomrule
\end{tabularx}
\end{table}

Next, construct the Huffman tree using a min-heap:
\begin{enumerate}
    \item Initial min-heap contents (ordered by frequency): $[C(1), D(1), B(2), R(2), A(5)]$.
    \item Extract $C(1)$ and $D(1)$. Create internal node $N_1$ with frequency $1 + 1 = 2$. Insert $N_1(2)$. Min-heap: $[B(2), R(2), N_1(2), A(5)]$.
    \item Extract $B(2)$ and $R(2)$. Create internal node $N_2$ with frequency $2 + 2 = 4$. Insert $N_2(4)$. Min-heap: $[N_1(2), N_2(4), A(5)]$.
    \item Extract $N_1(2)$ and $N_2(4)$. Create internal node $N_3$ with frequency $2 + 4 = 6$. Insert $N_3(6)$. Min-heap: $[A(5), N_3(6)]$.
    \item Extract $A(5)$ and $N_3(6)$. Create root node $R_{root}$ with frequency $5 + 6 = 11$.
\end{enumerate}

The finalized Huffman binary tree layout is shown below:

\begin{verbatim}
                   [Root: 11]
                  /          \
            (0)  /            \  (1)
                /              \
             [A: 5]          [N3: 6]
                            /       \
                      (0)  /         \  (1)
                          /           \
                      [N1: 2]       [N2: 4]
                      /     \       /     \
                (0)  /   (1) \ (0) /   (1) \
                    /         \   /         \
                 [C: 1]     [D: 1] [B: 2]   [R: 2]
\end{verbatim}

Navigating from the root to each leaf yields the code table:
\begin{table}[htbp]
\centering
\caption{Derived Huffman Codes and Bit Contributions}
\begin{tabularx}{0.8\textwidth}{>{\centering\arraybackslash}X >{\centering\arraybackslash}X >{\centering\arraybackslash}X >{\centering\arraybackslash}X}
\toprule
\textbf{Symbol} & \textbf{Frequency} & \textbf{Huffman Code} & \textbf{Total Bits} \\
\midrule
A & 5 & \texttt{0} & 5 \\
B & 2 & \texttt{110} & 6 \\
R & 2 & \texttt{111} & 6 \\
C & 1 & \texttt{100} & 3 \\
D & 1 & \texttt{101} & 3 \\
\bottomrule
\end{tabularx}
\end{table}

The encoded string representation becomes:
\[
\texttt{0 (A) 110 (B) 111 (R) 0 (A) 100 (C) 0 (A) 101 (D) 0 (A) 110 (B) 111 (R) 0 (A)}
\]
The total storage consumed is $5 + 6 + 6 + 3 + 3 = 23$ bits. Compared to the uncompressed 88 bits, Huffman coding achieves a $73.86\%$ space reduction for this message.

\section{Composite Data Structures for High-Performance Caching}

In-memory caching improves subsystem throughput by storing frequently queried data in fast RAM. Because cache memory capacity is limited, a cache must execute eviction strategies when full. The \textbf{least recently used cache} (LRU cache) evicts the item that has not been accessed for the longest duration.

An LRU cache requires two operations to execute in $O(1)$ worst-case time complexity:
\begin{itemize}
    \item \texttt{get(key)}: Retrieve the item value associated with the key and mark it as most recently used.
    \item \texttt{put(key, value)}: Insert or update a key-value pair. If capacity is exceeded, evict the least recently used item.
\end{itemize}

A single foundational data structure cannot satisfy both operational constraints simultaneously. Searching a doubly linked list requires $O(n)$ time, while a standard hash table cannot track item access recency in $O(1)$ time. 

The optimal architectural solution couples a hash table with a doubly linked list.

\subsection{LRU Cache Structural Integration}

The doubly linked list maintains the items in sequence of access recency. The head of the list stores the most recently accessed item, while the tail stores the least recently accessed item. The hash table maps search keys directly to list node pointers, bypassing linear list traversal.

\begin{verbatim}
  HASH TABLE
 +----------+--------------+
 |  Key     | Node Pointer |
 +----------+--------------+
 | "user_1" |    [P1]------|-----------------------+
 | "user_2" |    [P2]------|------------+          |
 +----------+--------------+            |          |
                                        v          v
  DOUBLY LINKED LIST                  +----+     +----+
  +------+    +---------------+       |Node|     |Node|       +---------------+    +------+
  | Head |<-->| Key: "user_2" |<----->|P2  |<--->|P1  |<----->| Key: "user_1" |<-->| Tail |
  | Dummy|    | Val: "Alice"  |       |... |     |... |       | Val: "Bob"    |    | Dummy|
  +------+    +---------------+       +----+     +----+       +---------------+    +------+
               (Most Recent)                                  (Least Recent)
\end{verbatim}

\subsection{Operational Execution Trace}

The composite LRU cache executes its core methods through joint state manipulation:

\subsubsection{Get Operation}
\begin{enumerate}
    \item Query the hash table with the key. If the key is absent, return a cache miss status.
    \item If the key is present, extract the direct memory pointer to the list node.
    \item Detach the node from its current position in the doubly linked list by modifying its neighbors' pointers in $O(1)$ time.
    \item Splice the node directly behind the list head node (marking it most recently used).
    \item Return the stored value.
\end{enumerate}

\subsubsection{Put Operation}
\begin{enumerate}
    \item Query the hash table with the key. If the key exists, update its value field and promote the node to the list head.
    \item If the key does not exist:
    \begin{enumerate}
        \item If the cache count equals capacity, retrieve the node preceding the tail dummy node (the least recently used node).
        \item Delete the key of the tail node from the hash table.
        \item Remove the tail node from the doubly linked list in $O(1)$ time.
        \item Allocate a new node containing the key and value, splice it behind the head node, and add its pointer reference to the hash table.
    \end{enumerate}
\end{enumerate}

\section{Database Indexing and Search Engine Retrieval}

Information retrieval and database systems process non-numeric data queries, such as text searches and prefix matching. Generic binary search trees or arrays are inefficient for large-scale string processing due to string comparison overheads. Specialized indexing structures address these operational constraints.

\subsection{Inverted Indexing}

An \textbf{inverted index} is a dictionary structure optimized for text retrieval across large document collections. Instead of mapping documents to contained words, an inverted index maps distinct terms to a list of document identification tags where those terms appear. This structure is known as a postings list.

\begin{verbatim}
  TERM DICTIONARY                      POSTINGS LISTS
  (Hash Table / Tree)                (Singly Linked Lists)
 +-------------------+             +----+    +----+    +----+
 | "algorithm"       |------------>| 12 |--->| 45 |--->| 89 |
 +-------------------+             +----+    +----+    +----+
 | "binary"          |------------>|  3 |--->| 45 |
 +-------------------+             +----+    +----+
 | "complexity"      |------------>| 12 |--->| 99 |
 +-------------------+             +----+    +----+
\end{verbatim}

Constructing an inverted index uses a hash table or search tree for the primary term dictionary, while storing postings as dynamic arrays or singly linked lists. To execute a boolean search query such as \texttt{"algorithm AND binary"}, the engine retrieves the posting lists for both terms and performs a linear list intersection algorithm in time proportional to the length of the lists.

\subsection{Prefix Search via Tries}

A \textbf{trie} (also termed a prefix tree) is a tree-based search data structure where nodes represent character keys rather than entire data items. The root node represents an empty key, and child nodes represent single-character extensions.

\begin{verbatim}
                       (Root)
                      /      \
                    'c'      'd'
                    /          \
                  'a'          'o'
                  / \           |
                't'  'r'       'g'
               (EOW)  /         (EOW)
                    't'
                   (EOW)
\end{verbatim}

In the trie above, the stored words are \texttt{"cat"}, \texttt{"cart"}, and \texttt{"dog"}. Nodes labeled \texttt{(EOW)} represent the end of a valid word.

Tries enable optimal string searching and auto-complete functionality. Searching for a string of length $k$ takes $O(k)$ time complexity, independent of the total number of keys stored in the dataset.

\section{Data Structure Selection in Applied Domains}

Selecting data structures requires evaluating operations, time complexities, and memory requirements against application objectives. Table \ref{tab:ds_comparison} compares the domain-specific data structures discussed in this chapter.

\begin{table}[htbp]
\centering
\caption{Comparison of Domain-Specific Data Structures}
\label{tab:ds_comparison}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{2.5cm} >{\raggedright\arraybackslash}p{3cm} >{\raggedright\arraybackslash}p{3cm} >{\raggedright\arraybackslash}X}
\toprule
\textbf{Structure} & \textbf{Core Operations} & \textbf{Time Complexity} & \textbf{Primary Domain} \\
\midrule
Huffman Tree & Bit insertion, Prefix code parsing & $O(n \log k)$ build, $O(k)$ decode per character & Lossless text and media compression \\
\addlinespace
LRU Cache & Key lookups, Node promotion and eviction & $O(1)$ for get and put & In-memory performance caching \\
\addlinespace
Inverted Index & Dictionary lookup, List intersection & $O(k)$ key search, $O(L_1 + L_2)$ intersection & Full-text search engine indexing \\
\addlinespace
Trie & String search, Prefix matching & $O(k)$ key lookup ($k =$ string length) & Auto-complete, IP packet routing \\
\bottomrule
\end{tabularx}
\end{table}

\section{Graph Structures in Network Routing}

Graph structures model connected networks such as the internet, road systems, and social graphs. Modern routing protocol engines rely on efficient graph representations coupled with priority queues to evaluate optimal signal pathways.

Dijkstra's shortest path algorithm calculates the minimum path distance from a single source vertex to all other vertices in a weighted graph.

The graph representation dictates algorithmic efficiency:
\begin{itemize}
    \item \textbf{Adjacency Matrix}: An $n \times n$ matrix providing $O(1)$ edge weight lookups, but requiring $O(V^2)$ total space complexity.
    \item \textbf{Adjacency List}: Array of linked lists storing only existing edges, consuming $O(V + E)$ space complexity, where $V$ is vertices and $E$ is edges.
\end{itemize}

\begin{verbatim}
  SAMPLE GRAPH              ADJACENCY MATRIX          ADJACENCY LIST
    (A)---(B)                 A  B  C  D             [A] -> B -> C
     |   /                   A 0  1  1  0             [B] -> A -> C -> D
     |  /                    B 1  0  1  1             [C] -> A -> B
    (C)---(D)                C 1  1  0  0             [D] -> B
                             D 0  1  0  0
\end{verbatim}

When Dijkstra's algorithm uses a flat array to scan unvisited vertices, the minimum distance selection takes $O(V)$ time per vertex, producing an overall runtime complexity of $O(V^2)$. 

By pairing an adjacency list graph representation with a min-heap priority queue, finding the minimum distance vertex executes in $O(\log V)$ time. This optimization reduces the overall algorithm execution time complexity to $O((V + E) \log V)$, enabling real-time routing over massive networks.

\section*{Tutorial Questions}

\begin{enumerate}
    \item Explain the prefix property in variable-length code systems. Describe the functional problems that arise during decoding if a set of codes violates this property.
    \item Construct a Huffman code tree for a document containing the following character counts: \texttt{E: 12}, \texttt{T: 9}, \texttt{A: 8}, \texttt{I: 4}, \texttt{O: 2}. List the binary code generated for each character and compute the total bits required to encode the source document.
    \item An LRU cache with a total capacity of 3 items processes the following sequence of execution calls:
    \begin{verbatim}
    put("A", 1), put("B", 2), put("C", 3), get("A"), put("D", 4)
    \end{verbatim}
    Draw the contents of both the hash table and the doubly linked list after each operation completes. Identify which key is evicted upon inserting \texttt{("D", 4)}.
    \item Compare the storage efficiency and time performance of a hash table versus a trie for storing a dictionary of 500,000 text strings. Highlight conditions under which a trie is preferred.
    \item Explain how an inverted index executes multi-word intersection queries (such as \texttt{"data AND structure"}). State the worst-case time complexity of intersecting two posting lists of lengths $M$ and $N$.
    \item Analyze the algorithmic impact of data structure selection in Dijkstra's shortest path algorithm. Contrast the theoretical performance of an implementation using a linear array versus one using a min-heap priority queue.
    \item A network router needs to match incoming IP addresses to a table of 100,000 network prefixes in real time. Choose an appropriate data structure for this application domain, justify your selection over alternative structures, and analyze its search time complexity.
\end{enumerate}

\section*{Conclusion}

Data structures are non-isolated theoretical models; they serve as structural primitives that power software engineering solutions across modern applications. As demonstrated throughout this chapter, complex domain applications, including lossless compression engines, operating system memory caches, full-text search indexes, and network packet routers, require combining foundational data structures to meet real-world computational constraints. Combining hashing, tree models, linked sequences, and priority queues allows systems to optimize execution time and space utilization simultaneously, translating theoretical complexity bounds into scalable software architectures. Having examined how composite data structures optimize resource efficiency in production systems, the next step is to explore how algorithmic design paradigms—such as greedy strategies, divide-and-conquer, and dynamic programming—leverage these underlying structures to solve complex computational problems.


