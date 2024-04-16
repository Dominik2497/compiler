from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *

def identToWasmId(ident: Ident) -> WasmId:
    return WasmId('$' + ident.name)

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case StmtExp():
                wasmInstructions.extend(compileExpressions(stmt.exp))
            case Assign(var, right):
                wasmInstructions.extend(compileExpressions(right))
                wasmInstructions.append(WasmInstrVarLocal(op='set', id=WasmId('$' + var.name)))
            case IfStmt(cond, thenBody, elseBody):
                thenInstrs = compileStmts(thenBody)
                elseInstrs = compileStmts(elseBody)
                condInstrs = compileExpressions(cond)

                instrs: list[WasmInstr] = []
                instrs.extend(condInstrs)

                instrs.append(WasmInstrIf(None, thenInstrs, elseInstrs))

                wasmInstructions.extend(instrs)

            case WhileStmt(cond, body):
                loopStartLabel = WasmId('$loopstart')
                loopEndLabel = WasmId('$loopend') 
                instrs: list[WasmInstr] = []

                bodyInstrs = compileStmts(body)
                condInstrs = compileExpressions(cond)

                whileBody: list[WasmInstr] = []
                whileBody += condInstrs
                whileBody.append(WasmInstrIf(None, [],
                            [WasmInstrBranch(loopEndLabel, False)]))
                whileBody.extend(bodyInstrs)
                whileBody.append(WasmInstrBranch(loopStartLabel, False))

                instrs.append(WasmInstrBlock(loopEndLabel, None, [
                    WasmInstrLoop(loopStartLabel, whileBody),
                ])) 

                wasmInstructions.extend(instrs)

    return wasmInstructions


def compileExpressions(exp: exp) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = [] 

    match exp:
        case IntConst(value):
            wasmInstructions.append(WasmInstrConst('i64', value))
        case Call(name):
            wasmInstructions.extend(compileCall(exp))
        case UnOp(op_var, sub):
            match op_var:
                case USub():
                    wasmInstructions.append(WasmInstrConst(ty='i64', val=0))
                    wasmInstructions.extend(compileExpressions(sub))
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='sub'))
                case Not(): 
                    wasmInstructions.extend(compileExpressions(sub))
                    wasmInstructions.append(WasmInstrConst('i32', 0))
                    wasmInstructions.append(WasmInstrIntRelOp('i32', 'eq'))
        case BinOp(left, op, right):
            wasmInstructions += compileExpressions(left)
            wasmInstructions += compileExpressions(right)
            wasmInstructionL = compileExpressions(left)
            wasmInstructionR = compileExpressions(right)
            match op:
                case Sub():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='sub'))
                case Add():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='add'))
                case Mul():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='mul'))
                case Less():
                    wasmInstructions.append(WasmInstrIntRelOp(ty='i64', op='lt_s'))
                case LessEq():
                    wasmInstructions.append(WasmInstrIntRelOp(ty='i64', op='le_s'))
                case Greater():
                    wasmInstructions.append(WasmInstrIntRelOp(ty='i64', op='gt_s'))
                case GreaterEq():
                    wasmInstructions.append(WasmInstrIntRelOp(ty='i64', op='ge_s'))
                case Eq():
                    if isinstance(left, BoolConst) and isinstance(right, BoolConst):
                        wasmInstructions.append(WasmInstrIntRelOp(ty='i32',op='eq'))
                    else:
                        wasmInstructions.append(WasmInstrIntRelOp(ty='i64',op='eq'))
                case NotEq():
                    wasmInstructions.append(WasmInstrIntRelOp(ty='i64',op='ne'))
                case And():
                    wasmInstructions: list[WasmInstr] = []
                    wasmInstructions+= wasmInstructionL
                    wasmInstructions.append(WasmInstrIf('i32',wasmInstructionR, [WasmInstrConst('i32',0)]))
                case Or():
                    wasmInstructions: list[WasmInstr] = []
                    wasmInstructions+= wasmInstructionL
                    wasmInstructions.append(WasmInstrIf('i32', [WasmInstrConst('i32',1)], compileExpressions(right)))
        case Name(name):
            wasmInstructions.append(WasmInstrVarLocal(op='get', id=identToWasmId(name)))
        case BoolConst(value):
            wasmInstructions.append(WasmInstrConst('i32', int(value)))
    return wasmInstructions

    
def compileCall(call: Call) -> list[WasmInstr]:
    match call:
        case Call(Ident('print'), args):
            return compilePrint_i64(args)
        case Call(Ident('input_int'), args):
            return [WasmInstrCall(WasmId('$input_i64'))]
        case _:
            raise ValueError("wrong function call: ", call)

def compilePrint_i64(args: list[exp]) -> list[WasmInstr]:
    instructions: list[WasmInstr] = []
    for arg in args:
        instructions.extend(compileExpressions(arg))
    instructions.append(WasmInstrCall(WasmId('$print_i64')))
    return instructions

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals_ = [(identToWasmId(x), 'i64' if isinstance(info.ty, Int) else 'i32') for x, info in vars.items()]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
                      exports=[WasmExport("main", WasmExportFunc(idMain))],
                      globals=[],
                      data=[],
                      funcTable=WasmFuncTable([]),
                      funcs=[WasmFunc(idMain, [], None, locals_, instrs)])






 