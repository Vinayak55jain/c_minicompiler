"""
Code generator: walks the AST and emits x86-64 AT&T syntax assembly
suitable for GAS (GNU Assembler) / gcc.

Strategy:
  - Stack-based locals (rbp-relative offsets)
  - Expression evaluation via rax, with intermediates pushed/popped
  - System V AMD64 ABI for calls (rdi, rsi, rdx, rcx, r8, r9)
  - String literals in .rodata
"""
from ast_nodes import *
from io import StringIO


class CodeGenError(Exception):
    pass


class CodeGen:
    def __init__(self):
        self.out = StringIO()
        self.rodata: list[str] = []      # string literal declarations
        self.str_count = 0
        self.label_count = 0
        self.local_offsets: dict[str, int] = {}
        self.stack_size = 0
        self.current_func = ''
        self.arg_regs = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']

    def emit(self, line: str):
        self.out.write(line + '\n')

    def ins(self, op: str, *args):
        """Emit indented instruction."""
        self.emit('    ' + op + (' ' + ', '.join(args) if args else ''))

    def label(self, name: str):
        self.emit(name + ':')

    def new_label(self, prefix='L') -> str:
        self.label_count += 1
        return f'.{prefix}{self.label_count}'

    def new_str_label(self) -> str:
        self.str_count += 1
        return f'.Lstr{self.str_count}'

    def generate(self, program: Program) -> str:
        self.emit('.text')
        for decl in program.decls:
            if isinstance(decl, FuncDecl) and decl.body:
                self.gen_func(decl)
        # Global vars
        globals_code = []
        for decl in program.decls:
            if isinstance(decl, VarDecl):
                globals_code.append(f'.comm {decl.name},4,4')
        if globals_code:
            self.emit('')
            self.emit('.bss')
            for g in globals_code:
                self.emit('    ' + g)
        # String literals
        if self.rodata:
            self.emit('')
            self.emit('.section .rodata')
            for s in self.rodata:
                self.emit(s)
        return self.out.getvalue()

    def gen_func(self, func: FuncDecl):
        self.current_func = func.name
        self.local_offsets = {}
        self.stack_size = 0

        
        total = self.measure_locals(func.body, func.params)
        total = (total + 15) & ~15

        self.emit('')
        self.emit(f'.globl {func.name}')
        self.emit(f'.type {func.name}, @function')
        self.label(func.name)
        self.ins('pushq', '%rbp')
        self.ins('movq', '%rsp, %rbp')
        if total:
            self.ins('subq', f'${total}, %rsp')

        offset = 8 
        for i, param in enumerate(func.params[:6]):
            offset += 8
            self.local_offsets[param.name] = -offset
            self.ins('movq', f'{self.arg_regs[i]}, -{offset}(%rbp)')

        self.stack_size = offset
        self.gen_block(func.body)
        self.label(f'.{func.name}_ret')
        self.ins('movq', '%rbp, %rsp')
        self.ins('popq', '%rbp')
        self.ins('ret')
        self.emit(f'.size {func.name}, .-{func.name}')

    def measure_locals(self, block, params) -> int:
        """Count bytes needed for all locals in function."""
        n = len(params) * 8
        n += self._count_block(block)
        return n

    def _count_block(self, node) -> int:
        if isinstance(node, Block):
            return sum(self._count_block(s) for s in node.stmts)
        if isinstance(node, VarDecl):
            sz = node.array_size * 8 if node.array_size else 8
            return sz
        if isinstance(node, IfStmt):
            r = self._count_block(node.then_branch)
            if node.else_branch:
                r += self._count_block(node.else_branch)
            return r
        if isinstance(node, (WhileStmt, ForStmt)):
            b = node.body if hasattr(node, 'body') else node.then_branch
            r = self._count_block(b)
            if isinstance(node, ForStmt) and node.init:
                r += self._count_block(node.init)
            return r
        return 0

    def alloc_local(self, name: str, size: int = 8) -> int:
        self.stack_size += size
        offset = -self.stack_size
        self.local_offsets[name] = offset
        return offset

    def gen_block(self, block: Block):
        for stmt in block.stmts:
            self.gen_stmt(stmt)

    def gen_stmt(self, stmt):
        if isinstance(stmt, VarDecl):
            self.gen_var_decl(stmt)
        elif isinstance(stmt, ExprStmt):
            self.gen_expr(stmt.expr)
        elif isinstance(stmt, Block):
            self.gen_block(stmt)
        elif isinstance(stmt, IfStmt):
            self.gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.gen_while(stmt)
        elif isinstance(stmt, ForStmt):
            self.gen_for(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.gen_return(stmt)
        else:
            raise CodeGenError(f"Unknown stmt type: {type(stmt)}")

    def gen_var_decl(self, stmt: VarDecl):
        size = stmt.array_size * 4 if stmt.array_size else 8
        if stmt.name not in self.local_offsets:
            self.alloc_local(stmt.name, size)
        if stmt.init and not stmt.array_size:
            self.gen_expr(stmt.init)
            off = self.local_offsets[stmt.name]
            self.ins('movq', f'%rax, {off}(%rbp)')

    def gen_if(self, stmt: IfStmt):
        else_lbl = self.new_label('else')
        end_lbl = self.new_label('endif')
        self.gen_expr(stmt.cond)
        self.ins('testq', '%rax, %rax')
        self.ins('jz', else_lbl)
        self.gen_stmt(stmt.then_branch)
        if stmt.else_branch:
            self.ins('jmp', end_lbl)
        self.label(else_lbl)
        if stmt.else_branch:
            self.gen_stmt(stmt.else_branch)
            self.label(end_lbl)

    def gen_while(self, stmt: WhileStmt):
        cond_lbl = self.new_label('wcond')
        end_lbl = self.new_label('wend')
        self.label(cond_lbl)
        self.gen_expr(stmt.cond)
        self.ins('testq', '%rax, %rax')
        self.ins('jz', end_lbl)
        self.gen_stmt(stmt.body)
        self.ins('jmp', cond_lbl)
        self.label(end_lbl)

    def gen_for(self, stmt: ForStmt):
        cond_lbl = self.new_label('fcond')
        end_lbl = self.new_label('fend')
        if stmt.init:
            self.gen_stmt(stmt.init)
        self.label(cond_lbl)
        if stmt.cond:
            self.gen_expr(stmt.cond)
            self.ins('testq', '%rax, %rax')
            self.ins('jz', end_lbl)
        self.gen_stmt(stmt.body)
        if stmt.incr:
            self.gen_expr(stmt.incr)
        self.ins('jmp', cond_lbl)
        self.label(end_lbl)

    def gen_return(self, stmt: ReturnStmt):
        if stmt.value:
            self.gen_expr(stmt.value)
        self.ins('jmp', f'.{self.current_func}_ret')

    def gen_expr(self, expr):
        if isinstance(expr, IntLiteral):
            self.ins('movq', f'${expr.value}, %rax')

        elif isinstance(expr, CharLiteral):
            self.ins('movq', f'${expr.value}, %rax')

        elif isinstance(expr, StringLiteral):
            lbl = self.new_str_label()
            escaped = expr.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t').replace('\0', '\\0')
            self.rodata.append(f'{lbl}:')
            self.rodata.append(f'    .string "{escaped}"')
            self.ins('leaq', f'{lbl}(%rip), %rax')

        elif isinstance(expr, Identifier):
            if expr.name in self.local_offsets:
                off = self.local_offsets[expr.name]
                self.ins('movq', f'{off}(%rbp), %rax')
            else:
                # Global
                self.ins('movq', f'{expr.name}(%rip), %rax')

        elif isinstance(expr, BinOp):
            self.gen_binop(expr)

        elif isinstance(expr, UnaryOp):
            self.gen_unary(expr)

        elif isinstance(expr, Assign):
            self.gen_assign(expr)

        elif isinstance(expr, Call):
            self.gen_call(expr)

        elif isinstance(expr, ArrayIndex):
            self.gen_array_index(expr)

        elif isinstance(expr, AddrOf):
            self.gen_addr_of(expr.expr)

        elif isinstance(expr, Deref):
            self.gen_expr(expr.expr)
            self.ins('movq', '(%rax), %rax')

        else:
            raise CodeGenError(f"Unknown expr type: {type(expr)}")

    def gen_binop(self, expr: BinOp):
        
        self.gen_expr(expr.left)
        self.ins('pushq', '%rax')
        self.gen_expr(expr.right)
        self.ins('movq', '%rax, %rcx')  
        self.ins('popq', '%rax')          

        op = expr.op
        if op == '+':
            self.ins('addq', '%rcx, %rax')
        elif op == '-':
            self.ins('subq', '%rcx, %rax')
        elif op == '*':
            self.ins('imulq', '%rcx, %rax')
        elif op in ('/', '%'):
            self.ins('cqto')
            self.ins('idivq', '%rcx')
            if op == '%':
                self.ins('movq', '%rdx, %rax')
        elif op in ('==', '!=', '<', '>', '<=', '>='):
            self.ins('cmpq', '%rcx, %rax')
            setcc = {'==': 'sete', '!=': 'setne', '<': 'setl',
                     '>': 'setg', '<=': 'setle', '>=': 'setge'}[op]
            self.ins(setcc, '%al')
            self.ins('movzbq', '%al, %rax')
        elif op == '&&':
            
            self.ins('testq', '%rax, %rax')
            self.ins('setne', '%al')
            self.ins('testq', '%rcx, %rcx')
            self.ins('setne', '%cl')
            self.ins('andb', '%cl, %al')
            self.ins('movzbq', '%al, %rax')
        elif op == '||':
            self.ins('orq', '%rcx, %rax')
            self.ins('setne', '%al')
            self.ins('movzbq', '%al, %rax')

    def gen_unary(self, expr: UnaryOp):
        if expr.prefix:
            if expr.op == '-':
                self.gen_expr(expr.operand)
                self.ins('negq', '%rax')
            elif expr.op == '!':
                self.gen_expr(expr.operand)
                self.ins('testq', '%rax, %rax')
                self.ins('sete', '%al')
                self.ins('movzbq', '%al, %rax')
            elif expr.op == '++':
                self.gen_addr_of(expr.operand)
                self.ins('incq', '(%rax)')
                self.ins('movq', '(%rax), %rax')
            elif expr.op == '--':
                self.gen_addr_of(expr.operand)
                self.ins('decq', '(%rax)')
                self.ins('movq', '(%rax), %rax')
        else:  # postfix
            if expr.op == '++':
                self.gen_addr_of(expr.operand)
                self.ins('movq', '(%rax), %rcx')
                self.ins('incq', '(%rax)')
                self.ins('movq', '%rcx, %rax')
            elif expr.op == '--':
                self.gen_addr_of(expr.operand)
                self.ins('movq', '(%rax), %rcx')
                self.ins('decq', '(%rax)')
                self.ins('movq', '%rcx, %rax')

    def gen_assign(self, expr: Assign):
        self.gen_expr(expr.value)
        if expr.op == '+=':
            # load target, add, store
            self.ins('pushq', '%rax')
            self.gen_addr_of(expr.target)
            self.ins('popq', '%rcx')
            self.ins('addq', '%rcx, (%rax)')
            self.ins('movq', '(%rax), %rax')
        elif expr.op == '-=':
            self.ins('pushq', '%rax')
            self.gen_addr_of(expr.target)
            self.ins('popq', '%rcx')
            self.ins('subq', '%rcx, (%rax)')
            self.ins('movq', '(%rax), %rax')
        else:  # '='
            self.ins('pushq', '%rax')
            self.gen_addr_of(expr.target)
            self.ins('popq', '%rcx')
            self.ins('movq', '%rcx, (%rax)')
            self.ins('movq', '%rcx, %rax')

    def gen_call(self, expr: Call):
        
        args = expr.args
        
        for arg in reversed(args):
            self.gen_expr(arg)
            self.ins('pushq', '%rax')
       
        for i in range(min(len(args), 6)):
            self.ins('popq', self.arg_regs[i])
       
        self.ins('xorb', '%al, %al')  
        self.ins('call', expr.name)

    def gen_array_index(self, expr: ArrayIndex):
        """Load value at array[index]."""
        self.gen_addr_of(expr)
        self.ins('movq', '(%rax), %rax')

    def gen_addr_of(self, expr):
        """Compute address of lvalue into %rax."""
        if isinstance(expr, Identifier):
            if expr.name in self.local_offsets:
                off = self.local_offsets[expr.name]
                self.ins('leaq', f'{off}(%rbp), %rax')
            else:
                self.ins('leaq', f'{expr.name}(%rip), %rax')
        elif isinstance(expr, ArrayIndex):
            # addr = base + index * element_size
            self.gen_expr(expr.index)
            self.ins('pushq', '%rax')
            self.gen_addr_of(expr.array)
            self.ins('popq', '%rcx')
            self.ins('imulq', '$8, %rcx')
            self.ins('addq', '%rcx, %rax')
        elif isinstance(expr, Deref):
            self.gen_expr(expr.expr)  # pointer value
        elif isinstance(expr, AddrOf):
            self.gen_addr_of(expr.expr)
        else:
            raise CodeGenError(f"Cannot take address of {type(expr).__name__}")