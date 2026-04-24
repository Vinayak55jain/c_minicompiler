# Mini C Compiler

A mini C compiler written in Python that translates a subset of C into x86-64 AT&T syntax assembly. It covers all five classic compiler stages: lexing, parsing, semantic analysis, and code generation.

---

## Features

- Supports `int`, `char`, and `void` types with pointer support (`*`, `&`)
- Keywords: `if`, `else`, `while`, `for`, `return`
- Operators: arithmetic, comparison, logical, assignment (`+=`, `-=`, `++`, `--`)
- Arrays: declaration and indexing (`int arr[10]`, `arr[i]`)
- Function declarations and calls (up to 6 parameters via System V ABI)
- String and character literals
- Single-line (`//`) and multi-line (`/* */`) comments
- Built-in functions pre-registered: `printf`, `scanf`, `malloc`, `free`, `strlen`, `strcpy`, `strcmp`, `puts`, `getchar`, `putchar`, `exit`
- Emits x86-64 AT&T assembly, assemblable with GAS / `gcc`

---

## Folder Structure

```
compiler/
├── compiler.py        ← main driver and CLI entry point
├── lexer.py           ← tokenizer (source → tokens)
├── parser.py          ← recursive-descent parser (tokens → AST)
├── semantic.py        ← type checker and symbol table (validates AST)
├── codegen.py         ← x86-64 assembly generator (AST → .s file)
├── ast_nodes.py       ← AST node dataclass definitions
├── README.md          ← this file
└── tests/
    └── max_sum_subarray.c   ← sliding window test: max sum subarray of size k
```

---

## Requirements

- Python 3.10+
- `gcc` (optional — needed to assemble and link the generated `.s` file into a runnable binary)

No third-party Python packages are required.

---

## Installation

```bash
git clone <your-repo-url>
cd compiler
```

That's it. No build step needed.

---

## Usage

### Compile a `.c` file

```bash
python compiler.py hello.c -o hello
```

This writes `hello.s` (assembly) and links it into the `hello` binary using `gcc`.

### Compile and run immediately

```bash
python compiler.py hello.c -o hello --run
```

### Print the generated assembly

```bash
python compiler.py hello.c --emit-asm
```

### Debug: print tokens

```bash
python compiler.py hello.c --emit-tokens
```

### Debug: print the AST

```bash
python compiler.py hello.c --emit-ast
```

### Run the built-in test suite

```bash
python compiler.py --test
```

### Run a specific built-in test

```bash
python compiler.py --test-name fibonacci --run
```

### All CLI flags

| Flag | Description |
|---|---|
| `<source.c>` | C source file to compile |
| `-o <file>` | Output binary name (default: `a.out`) |
| `--emit-tokens` | Print token stream to stdout |
| `--emit-ast` | Print AST to stdout |
| `--emit-asm` | Print generated assembly to stdout |
| `--test` | Run all built-in tests |
| `--test-name <name>` | Run a single built-in test by name |
| `--run` | Execute the compiled binary after linking |

---

## Compilation Pipeline

```
Source (.c)
    │
    ▼
Lexer          → token list         (lexer.py)
    │
    ▼
Parser         → AST                (parser.py)
    │
    ▼
Semantic       → validated AST      (semantic.py)
    │
    ▼
Code Generator → x86-64 assembly    (codegen.py)
    │
    ▼
gcc / GAS      → binary executable
```

### Lexer (`lexer.py`)

Reads raw C source and produces a flat list of typed tokens. Handles all C operators, keywords, string/char literals, integers, and both comment styles.

### Parser (`parser.py`)

Recursive-descent parser implementing full C expression precedence (assignment → logical or → logical and → equality → relational → additive → multiplicative → unary → postfix → primary). Builds an AST of dataclass nodes defined in `ast_nodes.py`.

### Semantic analyser (`semantic.py`)

Two-pass analysis: registers all function signatures in the first pass, then walks every function body checking variable declarations, use-before-declare errors, and type propagation. Decorates AST nodes with `.ctype` attributes used by the code generator.

### Code generator (`codegen.py`)

Walks the AST and emits x86-64 AT&T syntax assembly. Uses rbp-relative stack slots for all locals, and the System V AMD64 ABI (`rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`) for function calls. String literals go into `.rodata`.

---

## Built-in Tests

The following programs are bundled inside `compiler.py` and run with `--test`:

| Name | Description |
|---|---|
| `hello_world` | Prints "Hello, World!" |
| `fibonacci` | Recursive Fibonacci, first 10 numbers |
| `factorial` | Recursive factorial of 5 and 10 |
| `counter` | While loop counting 0–4 |
| `bubble_sort` | Sorts an array of 5 integers |
| `pointers` | Swaps two integers via pointer arguments |

---

## Tests Folder

The `tests/` folder contains standalone `.c` files you can compile directly.

### `tests/max_sum_subarray.c` — sliding window: max sum subarray of size k

Implements the classic fixed-size sliding window algorithm. Given an array and window size `k`, finds the maximum sum of any contiguous subarray of length `k` in O(n) time.

**Algorithm:**

1. Compute the sum of the first `k` elements as the initial window.
2. Slide the window one step at a time: add the incoming element, subtract the outgoing element.
3. Track the maximum sum seen across all windows.

**Test cases:**

| # | Input array | k | Expected | Notes |
|---|---|---|---|---|
| TC1 | `[2, 1, 5, 1, 3, 2]` | 3 | 9 | Window `[5, 1, 3]` |
| TC2 | `[2, 3, 4, 1, 5]` | 2 | 7 | Window `[3, 4]` |
| TC3 | `[1, 4, 2, 10, 23, 3, 1, 0, 20]` | 4 | 39 | Window `[2, 10, 23, 3]` |
| TC4 | `[-1, -2, -3, -4]` | 2 | -3 | All-negative array |
| TC5 | `[5]` | 1 | 5 | Single element |
| TC6 | `[2, 1, 5, 1, 3, 2]` | 10 | -1 | k > n edge case |

**Compile and run:**

```bash
python compiler.py tests/max_sum_subarray.c -o max_sum --run
```

**Expected output:**

```
=== Max Sum Subarray of Size K ===
TC1: arr=[2,1,5,1,3,2] k=3  ->  9  (expected 9)
TC2: arr=[2,3,4,1,5]   k=2  ->  7  (expected 7)
TC3: arr=[1,4,2,10,23,3,1,0,20] k=4 -> 39  (expected 39)
TC4: arr=[-1,-2,-3,-4] k=2  -> -3  (expected -3)
TC5: arr=[5]           k=1  ->  5  (expected 5)
TC6: n<k edge case          -> -1  (expected -1)
```

---

## Supported C Subset

### Types
```c
int x;
char c;
void;
int* ptr;
char* str;
```

### Control flow
```c
if (x > 0) { ... } else { ... }
while (x < 10) { ... }
for (i = 0; i < n; i++) { ... }
return x;
```

### Operators
```c
+ - * / %          // arithmetic
== != < > <= >=    // comparison
&& ||  !           // logical
= += -=            // assignment
++ --              // increment / decrement (prefix and postfix)
& *                // address-of, dereference
```

### Arrays and pointers
```c
int arr[10];
arr[0] = 5;
int* p = &arr[0];
*p = 99;
```

### Functions
```c
int add(int a, int b) {
    return a + b;
}
```

---

## Known Limitations

- No `#include` — standard library functions (`printf`, etc.) are pre-registered as builtins
- No struct, union, enum, or typedef
- No floating-point types
- No array initializer syntax (`int a[] = {1, 2, 3}` is not supported — initialise element by element)
- Function pointers are not supported
- No preprocessor (`#define`, `#ifdef`, etc.)
- At most 6 function parameters (System V ABI register limit; stack-passed args not implemented)

---

## Example Program

```c
int fib(int n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i;
    for (i = 0; i < 10; i++) {
        printf("%d\n", fib(i));
    }
    return 0;
}
```

```bash
python compiler.py fib.c -o fib --run
```

---

## License

MIT
