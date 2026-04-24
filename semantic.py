"""
Semantic Analyser — symbol table, type checking, use-before-declare checks.
Decorates the AST with type information (adds .ctype attribute to nodes).
"""
from ast_nodes import *


class SemanticError(Exception):
    pass


class SymbolTable:
    def __init__(self, parent=None):
        self.table: dict[str, CType] = {}
        self.parent = parent

    def define(self, name: str, ctype: CType):
        if name in self.table:
            raise SemanticError(f"'{name}' already declared in this scope")
        self.table[name] = ctype

    def lookup(self, name: str) -> CType:
        if name in self.table:
            return self.table[name]
        if self.parent:
            return self.parent.lookup(name)
        raise SemanticError(f"Undeclared identifier '{name}'")

    def child(self):
        return SymbolTable(parent=self)


BUILTIN_FUNCS = {
    'printf':  (CType('int'), True),   
    'scanf':   (CType('int'), True),
    'malloc':  (CType('void', 1), False),
    'free':    (CType('void'), False),
    'exit':    (CType('void'), False),
    'strlen':  (CType('int'), False),
    'strcpy':  (CType('char', 1), False),
    'strcmp':  (CType('int'), False),
    'puts':    (CType('int'), False),
    'getchar': (CType('int'), False),
    'putchar': (CType('int'), False),
}


class SemanticAnalyser:
    def __init__(self):
        self.global_scope = SymbolTable()
        self.func_returns: dict[str, CType] = {}
        self.current_func: str | None = None
       
        for name, (ret, _) in BUILTIN_FUNCS.items():
            self.func_returns[name] = ret

    def error(self, msg):
        raise SemanticError(f"[Semantic] {msg}")

    def analyse(self, program: Program):
        # First pass: register all function signatures
        for decl in program.decls:
            if isinstance(decl, FuncDecl):
                self.func_returns[decl.name] = decl.ret_type
                self.global_scope.define(decl.name, decl.ret_type)
            elif isinstance(decl, VarDecl):
                self.global_scope.define(decl.name, decl.ctype)

        # Second pass: analyse bodies
        for decl in program.decls:
            if isinstance(decl, FuncDecl) and decl.body:
                self.analyse_func(decl)

    def analyse_func(self, func: FuncDecl):
        self.current_func = func.name
        scope = self.global_scope.child()
        for param in func.params:
            scope.define(param.name, param.ctype)
        self.analyse_block(func.body, scope)
        self.current_func = None

    def analyse_block(self, block: Block, scope: SymbolTable):
        local = scope.child()
        for stmt in block.stmts:
            self.analyse_stmt(stmt, local)

    def analyse_stmt(self, stmt, scope: SymbolTable):
        if isinstance(stmt, VarDecl):
            if stmt.init:
                self.analyse_expr(stmt.init, scope)
            scope.define(stmt.name, stmt.ctype)
            stmt.ctype = stmt.ctype  # already set

        elif isinstance(stmt, ExprStmt):
            self.analyse_expr(stmt.expr, scope)

        elif isinstance(stmt, Block):
            self.analyse_block(stmt, scope)

        elif isinstance(stmt, IfStmt):
            self.analyse_expr(stmt.cond, scope)
            self.analyse_stmt(stmt.then_branch, scope)
            if stmt.else_branch:
                self.analyse_stmt(stmt.else_branch, scope)

        elif isinstance(stmt, WhileStmt):
            self.analyse_expr(stmt.cond, scope)
            self.analyse_stmt(stmt.body, scope)

        elif isinstance(stmt, ForStmt):
            inner = scope.child()
            if stmt.init:
                self.analyse_stmt(stmt.init, inner)
            if stmt.cond:
                self.analyse_expr(stmt.cond, inner)
            if stmt.incr:
                self.analyse_expr(stmt.incr, inner)
            self.analyse_stmt(stmt.body, inner)

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                t = self.analyse_expr(stmt.value, scope)
                expected = self.func_returns.get(self.current_func)
                if expected and expected.name == 'void' and t and t.name != 'void':
                    pass  

    def analyse_expr(self, expr, scope: SymbolTable) -> CType | None:
        if isinstance(expr, IntLiteral):
            expr.ctype = CType('int')
            return expr.ctype

        elif isinstance(expr, CharLiteral):
            expr.ctype = CType('char')
            return expr.ctype

        elif isinstance(expr, StringLiteral):
            expr.ctype = CType('char', 1)
            return expr.ctype

        elif isinstance(expr, Identifier):
            t = scope.lookup(expr.name)
            expr.ctype = t
            return t

        elif isinstance(expr, BinOp):
            lt = self.analyse_expr(expr.left, scope)
            rt = self.analyse_expr(expr.right, scope)
            if expr.op in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
                expr.ctype = CType('int')
            else:
                expr.ctype = lt or rt or CType('int')
            return expr.ctype

        elif isinstance(expr, UnaryOp):
            t = self.analyse_expr(expr.operand, scope)
            if expr.op == '!':
                expr.ctype = CType('int')
            elif expr.op == '-':
                expr.ctype = t or CType('int')
            else:
                expr.ctype = t or CType('int')
            return expr.ctype

        elif isinstance(expr, Assign):
            self.analyse_expr(expr.target, scope)
            t = self.analyse_expr(expr.value, scope)
            expr.ctype = t
            return t

        elif isinstance(expr, Call):
            for arg in expr.args:
                self.analyse_expr(arg, scope)
            ret = self.func_returns.get(expr.name)
            if ret is None:
                try:
                    scope.lookup(expr.name)
                    ret = CType('int')
                except SemanticError:
                    self.error(f"Call to undeclared function '{expr.name}'")
            expr.ctype = ret
            return ret

        elif isinstance(expr, ArrayIndex):
            self.analyse_expr(expr.array, scope)
            self.analyse_expr(expr.index, scope)
            base = getattr(expr.array, 'ctype', CType('int'))
            if base.ptr > 0:
                expr.ctype = CType(base.base, base.ptr - 1)
            else:
                expr.ctype = CType(base.base)
            return expr.ctype

        elif isinstance(expr, Deref):
            t = self.analyse_expr(expr.expr, scope)
            if t and t.ptr > 0:
                expr.ctype = CType(t.base, t.ptr - 1)
            else:
                expr.ctype = CType('int')
            return expr.ctype

        elif isinstance(expr, AddrOf):
            t = self.analyse_expr(expr.expr, scope)
            expr.ctype = CType(t.base if t else 'int', (t.ptr if t else 0) + 1)
            return expr.ctype

        return None