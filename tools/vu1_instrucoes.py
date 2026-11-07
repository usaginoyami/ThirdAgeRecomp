"""Instrucoes do VU1 geradas direto em C++ para tools/vu1_tradutor.py.

Cada funcao devolve o C++ que substitui vu.execUpper(U) ou vu.execLower(L, ...) para uma palavra constante, ou None
(o gerador chama o interpretador). Cada caso e uma copia, linha a linha, do case correspondente de ps2_vu1_upper.cpp /
ps2_vu1_lower.cpp, com os campos ja resolvidos: mesma ordem de leitura e escrita, mesmos auxiliares do interpretador
(applyFmacDest, queueClip, queueStore, queueQ, readBranchVi), mesma aritmetica em float. O verificador de execucao dupla
(PS2X_VU1_VERIFICA) confere o resultado contra o interpretador.
"""

PISTAS = (8, 4, 2, 1)  # x, y, z, w no campo dest


def campos_superiores(u):
    return {'dest': (u >> 21) & 0xF, 'ft': (u >> 16) & 0x1F, 'fs': (u >> 11) & 0x1F, 'fd': (u >> 6) & 0x1F,
            'op': u & 0x3F, 'esp': (u & 0x3) | ((u >> 4) & 0x7C)}


def _vs(fs, c):
    return 'vuNorm(vu.m_state.vf[%d][%d])' % (fs, c)


def _fmac(u, destino_acc, formula):
    """formula(c) -> expressao com vs, vt, bc, q, i, acc ja normalizados (como no interpretador)."""
    f = campos_superiores(u)
    linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{']
    linhas.append('    float vs[4], vt[4], acc[4];')
    linhas.append('    for (int c = 0; c < 4; ++c) { vs[c] = vuNorm(vu.m_state.vf[%d][c]); vt[c] = vuNorm(vu.m_state.vf[%d][c]); acc[c] = vuNorm(vu.m_state.acc[c]); }' % (f['fs'], f['ft']))
    linhas.append('    const float q = vuNorm(vu.m_state.q); const float i = vuNorm(vu.m_state.i);')
    linhas.append('    (void)vt; (void)acc; (void)q; (void)i;')
    linhas.append('    float result[4];')
    for c in range(4):
        linhas.append('    result[%d] = %s;' % (c, formula(c)))
    if destino_acc:
        linhas.append('    vu.applyFmacDestAcc(result, %du);' % f['dest'])
    else:
        linhas.append('    vu.applyFmacDest(vu.m_state.vf[%d], result, %du);' % (f['fd'], f['dest']))
    linhas.append('}')
    return linhas


def _aplica(dst, dest, valores):
    """applyDest: so as pistas do campo dest."""
    return ['%s[%d] = %s;' % (dst, c, valores[c]) for c in range(4) if dest & PISTAS[c]]


def gera_superior(u):
    f = campos_superiores(u)
    op, esp, dest, ft, fs, fd = f['op'], f['esp'], f['dest'], f['ft'], f['fs'], f['fd']
    bcv = lambda b: 'vuNorm(vt[%d])' % b  # broadcast(vt, b) normaliza de novo um valor ja normalizado: igual
    if op < 0x3C:
        grupo, b = op >> 2, op & 3
        if op < 0x1C:
            formulas = {0: lambda c: 'vs[%d] + %s' % (c, bcv(b)), 1: lambda c: 'vs[%d] - %s' % (c, bcv(b)),
                        2: lambda c: 'acc[%d] + vs[%d] * %s' % (c, c, bcv(b)), 3: lambda c: 'acc[%d] - vs[%d] * %s' % (c, c, bcv(b)),
                        6: lambda c: 'vs[%d] * %s' % (c, bcv(b))}
            if grupo in formulas:
                return _fmac(u, False, formulas[grupo])
            if grupo in (4, 5):  # MAXbc / MINIbc: applyDest, sem flags
                cmp = '>' if grupo == 4 else '<'
                linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{',
                          '    const float bc = vuNorm(vu.m_state.vf[%d][%d]);' % (ft, b),
                          '    float r[4];']
                for c in range(4):
                    linhas.append('    { const float v = %s; r[%d] = (v %s bc) ? v : bc; }' % (_vs(fs, c), c, cmp))
                linhas += ['    ' + l for l in _aplica('vu.m_state.vf[%d]' % fd, dest, ['r[%d]' % c for c in range(4)])]
                linhas.append('}')
                return linhas
            return None
        formulas = {0x1C: ('vs[%d] * q', False), 0x1E: ('vs[%d] * i', False), 0x20: ('vs[%d] + q', False),
                    0x21: ('acc[%d] + vs[%d] * q', True), 0x22: ('vs[%d] + i', False), 0x23: ('acc[%d] + vs[%d] * i', True),
                    0x24: ('vs[%d] - q', False), 0x25: ('acc[%d] - vs[%d] * q', True), 0x26: ('vs[%d] - i', False),
                    0x27: ('acc[%d] - vs[%d] * i', True), 0x28: ('vs[%d] + vt[%d]', 'vv'), 0x29: ('acc[%d] + vs[%d] * vt[%d]', 'avv'),
                    0x2A: ('vs[%d] * vt[%d]', 'vv'), 0x2C: ('vs[%d] - vt[%d]', 'vv'), 0x2D: ('acc[%d] - vs[%d] * vt[%d]', 'avv')}
        if op in formulas:
            modelo, tipo = formulas[op]
            if tipo == 'vv':
                return _fmac(u, False, lambda c: modelo % (c, c))
            if tipo == 'avv':
                return _fmac(u, False, lambda c: modelo % (c, c, c))
            if tipo is True:
                return _fmac(u, False, lambda c: modelo % (c, c))
            return _fmac(u, False, lambda c: modelo % c)
        if op in (0x1D, 0x1F, 0x2B, 0x2F):  # MAXi, MINIi, MAX, MINI
            cmp = '>' if op in (0x1D, 0x2B) else '<'
            outro = 'vuNorm(vu.m_state.i)' if op in (0x1D, 0x1F) else None
            linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{', '    float r[4];']
            for c in range(4):
                b = outro or 'vuNorm(vu.m_state.vf[%d][%d])' % (ft, c)
                linhas.append('    { const float v = %s; const float w = %s; r[%d] = (v %s w) ? v : w; }' % (_vs(fs, c), b, c, cmp))
            linhas += ['    ' + l for l in _aplica('vu.m_state.vf[%d]' % fd, dest, ['r[%d]' % c for c in range(4)])]
            linhas.append('}')
            return linhas
        return None
    # Grupo especial.
    if esp in (0x2F, 0x30):  # NOP
        return ['vu.m_currentUpperInstruction = 0x%08xu;' % u]
    grupo, b = esp >> 2, esp & 3
    if esp < 0x10 or 0x18 <= esp < 0x1C:
        formulas = {0: lambda c: 'vs[%d] + %s' % (c, bcv(b)), 1: lambda c: 'vs[%d] - %s' % (c, bcv(b)),
                    2: lambda c: 'acc[%d] + vs[%d] * %s' % (c, c, bcv(b)), 3: lambda c: 'acc[%d] - vs[%d] * %s' % (c, c, bcv(b)),
                    6: lambda c: 'vs[%d] * %s' % (c, bcv(b))}
        return _fmac(u, True, formulas[grupo])
    acc_form = {0x1C: 'vs[%d] * q', 0x1E: 'vs[%d] * i', 0x20: 'vs[%d] + q', 0x21: 'acc[%d] + vs[%d] * q',
                0x22: 'vs[%d] + i', 0x23: 'acc[%d] + vs[%d] * i', 0x24: 'vs[%d] - q', 0x25: 'acc[%d] - vs[%d] * q',
                0x26: 'vs[%d] - i', 0x27: 'acc[%d] - vs[%d] * i', 0x28: 'vs[%d] + vt[%d]', 0x29: 'acc[%d] + vs[%d] * vt[%d]',
                0x2A: 'vs[%d] * vt[%d]', 0x2C: 'vs[%d] - vt[%d]', 0x2D: 'acc[%d] - vs[%d] * vt[%d]'}
    if esp in acc_form:
        modelo = acc_form[esp]
        return _fmac(u, True, lambda c: modelo % ((c,) * modelo.count('%d')))
    if 0x10 <= esp <= 0x13:  # ITOF0/4/12/15
        div = {0x10: None, 0x11: '16.0f', 0x12: '4096.0f', 0x13: '32768.0f'}[esp]
        linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{', '    float r[4];']
        for c in range(4):
            conv = 'static_cast<float>(iv)' + (' / ' + div if div else '')
            linhas.append('    { int32_t iv; std::memcpy(&iv, &vu.m_state.vf[%d][%d], 4); r[%d] = %s; }' % (fs, c, c, conv))
        linhas += ['    ' + l for l in _aplica('vu.m_state.vf[%d]' % ft, dest, ['r[%d]' % c for c in range(4)])]
        linhas.append('}')
        return linhas
    if 0x14 <= esp <= 0x17:  # FTOI0/4/12/15
        escala = {0x14: '1.0f', 0x15: '16.0f', 0x16: '4096.0f', 0x17: '32768.0f'}[esp]
        linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{', '    float r[4];']
        for c in range(4):
            linhas.append('    { const int32_t iv = vuFloatToInt(%s, %s); std::memcpy(&r[%d], &iv, 4); }' % (_vs(fs, c), escala, c))
        linhas += ['    ' + l for l in _aplica('vu.m_state.vf[%d]' % ft, dest, ['r[%d]' % c for c in range(4)])]
        linhas.append('}')
        return linhas
    if esp == 0x1D:  # ABS
        linhas = ['vu.m_currentUpperInstruction = 0x%08xu;' % u, '{', '    float r[4];']
        for c in range(4):
            linhas.append('    r[%d] = std::fabs(%s);' % (c, _vs(fs, c)))
        linhas += ['    ' + l for l in _aplica('vu.m_state.vf[%d]' % ft, dest, ['r[%d]' % c for c in range(4)])]
        linhas.append('}')
        return linhas
    if esp == 0x1F:  # CLIP
        return ['vu.m_currentUpperInstruction = 0x%08xu;' % u,
                'vu.queueClip(vuClip(vu.m_state.vf[%d], vu.m_state.vf[%d][3]));' % (fs, ft)]
    return None


def _imm11(l):
    v = l & 0x7FF
    return v - 0x800 if v & 0x400 else v


def gera_inferior(l, pc):
    if l in (0x00000000, 0x8000033C):  # NOP: execLower volta antes de qualquer coisa
        return []
    op = (l >> 25) & 0x7F
    ft, fs = (l >> 16) & 0x1F, (l >> 11) & 0x1F
    vit, vis, vid = (l >> 16) & 0xF, (l >> 11) & 0xF, (l >> 6) & 0xF
    dest = (l >> 21) & 0xF
    if op == 0x00:  # LQ
        return ['{', '    uint32_t addr = ((uint32_t)(int32_t)(vu.m_state.vi[%d] + (int16_t)%d)) * 16u;' % (vis, _imm11(l)),
                '    addr &= (c.dataSize - 1);', '    if (addr + 16 <= c.dataSize)', '    {',
                '        float tmp[4]; std::memcpy(tmp, c.vuData + addr, 16);'] + \
               ['        ' + x for x in _aplica('vu.m_state.vf[%d]' % ft, dest, ['tmp[%d]' % k for k in range(4)])] + ['    }', '}']
    if op == 0x01:  # SQ
        return ['{', '    uint32_t addr = ((uint32_t)(int32_t)(vu.m_state.vi[%d] + (int16_t)%d)) * 16u;' % (vit, _imm11(l)),
                '    addr &= (c.dataSize - 1);', '    if (addr + 16 <= c.dataSize)', '    {',
                '        uint32_t words[4]; std::memcpy(words, vu.m_state.vf[%d], sizeof(words));' % fs,
                '        vu.queueStore(addr, words, %du);' % dest, '    }', '}']
    if op == 0x04:  # ILW
        comp = 0 if dest & 8 else 1 if dest & 4 else 2 if dest & 2 else 3
        linhas = ['{', '    uint32_t addr = ((uint32_t)(int32_t)(vu.m_state.vi[%d] + (int16_t)%d)) * 16u;' % (vis, _imm11(l)),
                  '    addr &= (c.dataSize - 1);', '    if (addr + 16 <= c.dataSize)', '    {',
                  '        uint32_t v; std::memcpy(&v, c.vuData + addr + %d * 4, 4);' % comp]
        if vit != 0:
            linhas.append('        vu.m_state.vi[%d] = (int32_t)(int16_t)(v & 0xFFFF);' % vit)
        else:
            linhas.append('        (void)v;')
        return linhas + ['    }', '}']
    if op in (0x08, 0x09):  # IADDIU / ISUBIU
        imm = (l & 0x7FF) | ((l >> 10) & 0x7800)
        if vit == 0:
            return []
        sinal = '+' if op == 0x08 else '-'
        return ['vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] %s (int16_t)%d);' % (vit, vis, sinal, imm)]
    if op == 0x10:  # FCEQ
        return ['vu.m_state.vi[1] = ((vu.m_state.clip & 0xFFFFFF) == 0x%xu) ? 1 : 0;' % (l & 0xFFFFFF)]
    if op == 0x12:  # FCAND
        return ['vu.m_state.vi[1] = ((vu.m_state.clip & 0x%xu) != 0) ? 1 : 0;' % (l & 0xFFFFFF)]
    if op == 0x13:  # FCOR
        return ['vu.m_state.vi[1] = ((vu.m_state.clip | 0x%xu) == 0xFFFFFF) ? 1 : 0;' % (l & 0xFFFFFF)]
    if op in (0x28, 0x29):  # IBEQ / IBNE: m_state.pc ainda e o PC do par
        cmp = '==' if op == 0x28 else '!='
        alvo = (pc + 8 + _imm11(l) * 8) & 0x3FFF
        return ['if ((int16_t)vu.readBranchVi(%d) %s (int16_t)vu.readBranchVi(%d))' % (vis, cmp, vit), '{',
                '    vu.m_state.branchPending = true;', '    vu.m_state.branchTarget = 0x%xu;' % alvo,
                '    vu.m_state.branchDelay = 1;', '}']
    if op == 0x40:
        funct = l & 0x3F
        if funct == 0x30:  # IADD
            return [] if vid == 0 else ['vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] + vu.m_state.vi[%d]);' % (vid, vis, vit)]
        if funct == 0x31:  # ISUB
            return [] if vid == 0 else ['vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] - vu.m_state.vi[%d]);' % (vid, vis, vit)]
        if funct == 0x32:  # IADDI
            imm5 = (l >> 6) & 0x1F
            imm5 = imm5 - 32 if imm5 & 0x10 else imm5
            return [] if vit == 0 else ['vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] + (int16_t)%d);' % (vit, vis, imm5)]
        if funct == 0x34:  # IAND
            return [] if vid == 0 else ['vu.m_state.vi[%d] = vu.m_state.vi[%d] & vu.m_state.vi[%d];' % (vid, vis, vit)]
        if funct == 0x35:  # IOR
            return [] if vid == 0 else ['vu.m_state.vi[%d] = vu.m_state.vi[%d] | vu.m_state.vi[%d];' % (vid, vis, vit)]
        if funct >= 0x3C:
            f2 = (l & 0x3) | ((l >> 4) & 0x7C)
            if f2 == 0x30:  # MOVE
                return ['{', '    float tmp[4]; std::memcpy(tmp, vu.m_state.vf[%d], 16);' % fs] + \
                       ['    ' + x for x in _aplica('vu.m_state.vf[%d]' % ft, dest, ['tmp[%d]' % k for k in range(4)])] + ['}']
            if f2 == 0x31:  # MR32
                return ['{', '    const float tmp[4] = {vu.m_state.vf[%d][1], vu.m_state.vf[%d][2], vu.m_state.vf[%d][3], vu.m_state.vf[%d][0]};' % (fs, fs, fs, fs)] + \
                       ['    ' + x for x in _aplica('vu.m_state.vf[%d]' % ft, dest, ['tmp[%d]' % k for k in range(4)])] + ['}']
            if f2 == 0x34:  # LQI
                linhas = ['{', '    uint32_t addr = ((uint32_t)(uint16_t)vu.m_state.vi[%d]) * 16u;' % vis, '    addr &= (c.dataSize - 1);',
                          '    if (addr + 16 <= c.dataSize)', '    {', '        float tmp[4]; std::memcpy(tmp, c.vuData + addr, 16);'] + \
                         ['        ' + x for x in _aplica('vu.m_state.vf[%d]' % ft, dest, ['tmp[%d]' % k for k in range(4)])] + ['    }']
                if vis != 0:
                    linhas.append('    vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] + 1);' % (vis, vis))
                return linhas + ['}']
            if f2 == 0x35:  # SQI
                linhas = ['{', '    uint32_t addr = ((uint32_t)(uint16_t)vu.m_state.vi[%d]) * 16u;' % vit, '    addr &= (c.dataSize - 1);',
                          '    if (addr + 16 <= c.dataSize)', '    {',
                          '        uint32_t words[4]; std::memcpy(words, vu.m_state.vf[%d], sizeof(words));' % fs,
                          '        vu.queueStore(addr, words, %du);' % dest, '    }']
                if vit != 0:
                    linhas.append('    vu.m_state.vi[%d] = (int16_t)(vu.m_state.vi[%d] + 1);' % (vit, vit))
                return linhas + ['}']
            if f2 == 0x38:  # DIV
                fsf, ftf = (l >> 21) & 3, (l >> 23) & 3
                return ['{', '    const float num = vuNorm(vu.m_state.vf[%d][%d]);' % (fs, fsf),
                        '    const float den = vuNorm(vu.m_state.vf[%d][%d]);' % (ft, ftf),
                        '    uint32_t statusDi = 0u; float result = 0.0f;',
                        '    if (den == 0.0f)', '    {', '        statusDi = num == 0.0f ? 0x10u : 0x20u;',
                        '        result = std::signbit(num) != std::signbit(den) ? -std::numeric_limits<float>::max() : std::numeric_limits<float>::max();',
                        '    }', '    else', '        result = num / den;',
                        '    uint32_t ignoredFlags = 0u;', '    result = vu.normalizeResult(result, ignoredFlags);',
                        '    vu.queueQ(result, 7u, statusDi);', '}']
            if f2 == 0x3B:  # WAITQ
                return []
    return None
