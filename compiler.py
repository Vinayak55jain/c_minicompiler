"""
Main compiler driver.

Usage:
    python compiler.py <source.c> [-o output] [--emit-tokens] [--emit-ast] [--emit-asm]
    python compiler.py --test    (run built-in test programs)

Compilation pipeline:
    source → lexer → parser → semantic → codegen → .s file
    Optionally assembles + links with gcc if available.
"""
import sys
import os
import subprocess
import argparse
import tempfile
import glob

from lexer import Lexer, LexError
from parser import Parser, ParseError
from semantic import SemanticAnalyser, SemanticError
from codegen import CodeGen, CodeGenError


def compile_source(source: str, filename: str = '<stdin>',
                   emit_tokens=False, emit_ast=False) -> str:
   
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    if emit_tokens:
        print(f"\n{'='*40}")
        print("TOKENS:")
        for tok in tokens:
            print(f"  {tok}")

   
    parser = Parser(tokens)
    ast = parser.parse()
    if emit_ast:
        print(f"\n{'='*40}")
        print("AST:")
        import pprint
        pprint.pprint(ast, width=100)

    
    analyser = SemanticAnalyser()
    analyser.analyse(ast)

    
    codegen = CodeGen()
    asm = codegen.generate(ast)
    return asm


def assemble_and_link(asm: str, output: str) -> bool:
    """Write .s, assemble + link via gcc. Returns True on success."""
    with tempfile.NamedTemporaryFile(suffix='.s', mode='w', delete=False) as f:
        f.write(asm)
        asm_file = f.name
    try:
        result = subprocess.run(
            ['gcc', '-no-pie', '-o', output, asm_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"[Linker] gcc error:\n{result.stderr}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print("[Warning] gcc not found — emitting .s file only", file=sys.stderr)
        return False
    finally:
        os.unlink(asm_file)




TESTS = {
    "fibonacci": """
int fib(int n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i;
    for (i = 0; i < 10; i++) {
        printf("%d\\n", fib(i));
    }
    return 0;
}
""",

    "bubble_sort": """
void sort(int arr[], int n) {
    int i;
    int j;
    int tmp;
    for (i = 0; i < n - 1; i++) {
        for (j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
        }
    }
}

int main() {
    int a[5];
    a[0] = 5;
    a[1] = 3;
    a[2] = 8;
    a[3] = 1;
    a[4] = 9;
    sort(a, 5);
    int i;
    for (i = 0; i < 5; i++) {
        printf("%d\\n", a[i]);
    }
    return 0;
}
""",

    "factorial": """
int fact(int n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}

int main() {
    printf("5! = %d\\n", fact(5));
    printf("10! = %d\\n", fact(10));
    return 0;
}
""",

    "hello_world": """
int main() {
    printf("Hello, World!\\n");
    return 0;
}
""",

    "counter": """
int main() {
    int x;
    x = 0;
    while (x < 5) {
        printf("x = %d\\n", x);
        x++;
    }
    return 0;
}
""",

    "pointers": """
void swap(int* a, int* b) {
    int tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
}

int main() {
    int x;
    int y;
    x = 10;
    y = 20;
    printf("before: x=%d y=%d\\n", x, y);
    swap(&x, &y);
    printf("after:  x=%d y=%d\\n", x, y);
    return 0;
}
""",
}


def run_tests(filter_name=None, emit_asm=False, run=False):
    passed = 0
    failed = 0
    for name, src in TESTS.items():
        if filter_name and name != filter_name:
            continue
        print(f"\n{'─'*50}")
        print(f"Test: {name}")
        print(f"{'─'*50}")
        try:
            asm = compile_source(src, name)
            if emit_asm:
                print("Assembly output:")
                for line in asm.splitlines():
                    print("  " + line)
            if run:
              
                exe = f'/tmp/test_{name}'
                if assemble_and_link(asm, exe):
                    result = subprocess.run([exe], capture_output=True, text=True, timeout=5)
                    print(f"Output:\n{result.stdout}")
                    if result.returncode != 0:
                        print(f"Exit code: {result.returncode}")
                    os.unlink(exe)
            print(f"✓ PASS")
            passed += 1
        except (LexError, ParseError, SemanticError, CodeGenError) as e:
            print(f"✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")


def compile_test_folder(test_dir, out_dir, emit_asm=False):
    if not os.path.isdir(test_dir):
        print(f"[Error] Test folder not found: {test_dir}", file=sys.stderr)
        return 1

    os.makedirs(out_dir, exist_ok=True)
    c_files = sorted(glob.glob(os.path.join(test_dir, '*.c')))
    if not c_files:
        print(f"No .c files found in {test_dir}")
        return 0

    passed = 0
    failed = 0
    for src_path in c_files:
        name = os.path.splitext(os.path.basename(src_path))[0]
        print(f"\n{'─'*50}")
        print(f"Compiling: {name}")
        print(f"{'─'*50}")
        try:
            with open(src_path, 'r') as f:
                source = f.read()
            asm = compile_source(source, src_path)
            out_path = os.path.join(out_dir, name + '.s')
            with open(out_path, 'w') as f:
                f.write(asm)
            print(f"Written assembly: {out_path}")
            if emit_asm:
                print("Assembly output:")
                for line in asm.splitlines():
                    print('  ' + line)
            passed += 1
        except (LexError, ParseError, SemanticError, CodeGenError) as e:
            print(f"✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Compiled: {passed} succeeded, {failed} failed")
    return 0 if failed == 0 else 1


def main():
    ap = argparse.ArgumentParser(description='Mini C Compiler')
    ap.add_argument('source', nargs='?', help='Source .c file')
    ap.add_argument('-o', '--output', default='a.out', help='Output file')
    ap.add_argument('--emit-tokens', action='store_true')
    ap.add_argument('--emit-ast', action='store_true')
    ap.add_argument('--emit-asm', action='store_true', help='Print assembly to stdout')
    ap.add_argument('--test', action='store_true', help='Run built-in tests')
    ap.add_argument('--test-name', help='Run a specific test by name')
    ap.add_argument('--compile-tests', action='store_true', help='Compile all .c files in a test folder to assembly output')
    ap.add_argument('--test-folder', default='tests', help='Folder containing C test files')
    ap.add_argument('--output-folder', default='output', help='Folder to write assembly files')
    ap.add_argument('--run', action='store_true', help='Run compiled output (requires gcc)')
    args = ap.parse_args()

    if args.test or args.test_name:
        run_tests(args.test_name, emit_asm=args.emit_asm, run=args.run)
        return

    if args.compile_tests:
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.test_folder)
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output_folder)
        sys.exit(compile_test_folder(test_dir, out_dir, emit_asm=args.emit_asm))

    if not args.source:
      
        print("Mini C Compiler — enter C source, end with EOF (Ctrl+D / Ctrl+Z)")
        source = sys.stdin.read()
    else:
        with open(args.source) as f:
            source = f.read()

    try:
        asm = compile_source(
            source,
            args.source or '<stdin>',
            emit_tokens=args.emit_tokens,
            emit_ast=args.emit_ast,
        )
    except (LexError, ParseError, SemanticError, CodeGenError) as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.emit_asm:
        print(asm)

    
    asm_out = args.output + '.s' if not args.output.endswith('.s') else args.output
    with open(asm_out, 'w') as f:
        f.write(asm)
    print(f"Assembly written to {asm_out}")

   
    if not args.output.endswith('.s'):
        if assemble_and_link(asm, args.output):
            print(f"Binary written to {args.output}")
            if args.run:
                result = subprocess.run([args.output], text=True)
                sys.exit(result.returncode)


if __name__ == '__main__':
    main()