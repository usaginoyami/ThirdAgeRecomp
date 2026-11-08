#!/usr/bin/env python3
"""vu1_tradutor.py pasta_do_censo saida.cpp [--minimo 0.5]

Gera os blocos traduzidos do VU1 a partir de uma rodada com PS2X_VU1_CENSO=1, que grava no diretorio da rodada:
  ps2x_vu1_censo.txt            pares executados, entradas e desvios tomados, por versao (hash) do codigo do VU1
  ps2x_vu1_decod_<hash>.txt     cada par decodificado pelo proprio interpretador, como inicializador C++

Para cada versao com pelo menos --minimo % dos pares, todos os pares executados viram constantes
(static constexpr DecodedInstructionPair) e executam com VU1Interpreter::passoPar, o mesmo codigo do interpretador.
Os blocos (lideres: entradas, destinos de desvio e o par depois de cada origem) sao rotulos de uma funcao por versao;
um switch no PC passa de um bloco a outro e devolve ao interpretador quando o PC nao e um lider.

A saida contem as palavras do microcodigo do jogo: vai para generated/ (ignorado pelo git), nunca para o repositorio.
"""
import argparse
import collections
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vu1_instrucoes  # noqa: E402


# ---- modo explicito (v2): o modelo de tempo de passoPar resolvido para as constantes de cada par ----

FDIV, EFU, BRANCH, XGKICK = 3, 4, 6, 7


def campos(inicializador):
    n = [int(t, 16) if t.startswith('0x') else int(t) for t in re.findall(r'0x[0-9a-fA-F]+|\d+', inicializador)]
    assert len(n) == 51, (len(n), inicializador)

    def uso(v):
        return {'vfRead': [(v[0], v[1]), (v[2], v[3])], 'vfWrite': (v[4], v[5]), 'vfReadCount': v[6], 'viRead': v[7],
                'viWrite': v[8], 'accRead': v[9], 'accWrite': v[10], 'latency': v[11], 'vfLatency': v[12],
                'viLatency': v[13], 'pipeline': v[14], 'waitQ': v[15], 'waitP': v[16], 'reserved': v[20],
                'delaysNextBranchRead': v[19]}
    return {'lower': n[0], 'upper': n[1], 'lo': uso(n[2:23]), 'up': uso(n[23:44]), 'iBit': n[44], 'eBit': n[45],
            'dBit': n[47], 'tBit': n[48], 'shadow': n[49], 'suppressed': n[50]}


def pista(c):
    return 1 << (3 - c)


def normaliza_operando(bits):
    expo = (bits >> 23) & 0xFF
    if expo == 0:
        return bits & 0x80000000
    if expo == 0xFF:
        return (bits & 0x80000000) | 0x7F7FFFFF
    return bits


def expressao_pronto(d):
    """Corpo de calculatePairReadyCycle com as constantes do par."""
    termos = []
    for u in (d['up'], d['lo']):
        for i in range(u['vfReadCount']):
            reg, lanes = u['vfRead'][i]
            for c in range(4):
                if lanes & pista(c):
                    termos.append('vu.m_vfReady[%d][%d]' % (reg, c))
        for reg in range(1, 16):
            if u['viRead'] & (1 << reg):
                termos.append('vu.m_viReady[%d]' % reg)
        for c in range(4):
            if u['accRead'] & pista(c):
                termos.append('vu.m_accReady[%d]' % c)
    lo = d['lo']
    extra = []
    if lo['pipeline'] == FDIV or lo['waitQ']:
        extra.append('if (vu.m_fdiv.valid) p = std::max(p, vu.m_fdiv.readyCycle);')
    if lo['pipeline'] == EFU:
        extra.append('p = std::max(p, vu.m_efuResourceReady);')
    if lo['waitP']:
        extra.append('for (const auto &e : vu.m_efu) if (e.valid) p = std::max(p, e.readyCycle);')
    if lo['pipeline'] == XGKICK:
        extra.append('if (vu.m_xgkick.active) p = std::max(p, vu.m_cycle + 1u);')
    return termos, extra


ESPECIALIZAR = True
# Avanco de ciclo embutido em cada par: medido mais lento (86,6 contra 76,8 ns por par com o verificador), pelo tamanho
# do codigo. Fica a chamada a advanceOneCycle; --avanco-embutido liga para comparar.
AVANCO_EMBUTIDO = False
CONTAGEM = {'sup': 0, 'sup_total': 0, 'inf': 0, 'inf_total': 0}


def exec_superior(u, w, recuo):
    CONTAGEM['sup_total'] += 1
    codigo = vu1_instrucoes.gera_superior(u) if ESPECIALIZAR else None
    if codigo is None:
        w(recuo + 'vu.execUpper(0x%08xu);' % u)
        return
    CONTAGEM['sup'] += 1
    for linha in codigo:
        w(recuo + linha)


def exec_inferior(l, u, pc, w, recuo):
    CONTAGEM['inf_total'] += 1
    codigo = vu1_instrucoes.gera_inferior(l, pc) if ESPECIALIZAR else None
    if codigo is None:
        w(recuo + 'vu.execLower(0x%08xu, c.vuData, c.dataSize, *c.gs, c.memory, 0x%08xu);' % (l, u))
        return
    CONTAGEM['inf'] += 1
    for linha in codigo:
        w(recuo + linha)


def gera_par(pc, d, w):
    lo, up = d['lo'], d['up']
    w('    // par 0x%x' % pc)
    w('    if (vu.m_cycle >= c.budgetEnd || vu.m_stopRequested || 0x%xu + 8u > c.codeSize) return VU1Interpreter::PassoPara;' % pc)
    termos, extra = expressao_pronto(d)
    if termos or extra:
        w('    {')
        w('        const auto pronto = [&]() -> uint64_t {')
        w('            uint64_t p = vu.m_cycle;')
        for t in termos:
            w('            p = std::max(p, %s);' % t)
        for e in extra:
            w('            ' + e)
        w('            return p;')
        w('        };')
        w('        uint64_t r = pronto();')
        w('        while (r > vu.m_cycle)')
        w('        {')
        w('            if (r >= c.budgetEnd) { vu.advanceTo(c.budgetEnd); break; }')
        w('            vu.advanceTo(r);')
        w('            r = pronto();')
        w('        }')
        w('        if (vu.m_cycle >= c.budgetEnd) return VU1Interpreter::PassoPara;')
        w('    }')

    vi_escrito = next((r for r in range(1, 16) if lo['viWrite'] & (1 << r)), 0)
    ureg, ulanes = up['vfWrite']
    lreg, llanes = lo['vfWrite']
    tem_up = ureg != 0
    tem_lo = lreg != 0 and d['suppressed'] != lreg
    lo_distinto = tem_lo and (not tem_up or lreg != ureg)
    w('    {')
    if vi_escrito:
        w('        const int32_t oldVi = vu.m_state.vi[%d];' % vi_escrito)
    if tem_up and ulanes != 15:
        w('        float oldUp[4]; std::memcpy(oldUp, vu.m_state.vf[%d], sizeof(oldUp));' % ureg)
    if lo_distinto and llanes != 15:
        w('        float oldLo[4]; std::memcpy(oldLo, vu.m_state.vf[%d], sizeof(oldLo));' % lreg)
    if up['accWrite'] not in (0, 15):
        w('        float oldAcc[4]; std::memcpy(oldAcc, vu.m_state.acc, sizeof(oldAcc));')
    if d['iBit']:
        exec_superior(d['upper'], w, '        ')
        w('        { const uint32_t bits = 0x%08xu; std::memcpy(&vu.m_state.i, &bits, sizeof(bits)); }' % normaliza_operando(d['lower']))
    elif d['shadow']:
        s = d['shadow']
        w('        float sombra[4]; float novo[4];')
        w('        std::memcpy(sombra, vu.m_state.vf[%d], sizeof(sombra));' % s)
        exec_superior(d['upper'], w, '        ')
        w('        std::memcpy(novo, vu.m_state.vf[%d], sizeof(novo));' % s)
        w('        std::memcpy(vu.m_state.vf[%d], sombra, sizeof(sombra));' % s)
        exec_inferior(d['lower'], d['upper'], pc, w, '        ')
        w('        std::memcpy(vu.m_state.vf[%d], novo, sizeof(novo));' % s)
    else:
        exec_superior(d['upper'], w, '        ')
        exec_inferior(d['lower'], d['upper'], pc, w, '        ')
    w('        vu.m_viBranchBackupValid = false;')
    # Escrita imediata: pistas fora da mascara voltam ao valor antigo.
    if tem_up and ulanes != 15:
        for c in range(4):
            if not ulanes & pista(c):
                w('        vu.m_state.vf[%d][%d] = oldUp[%d];' % (ureg, c, c))
    if lo_distinto and llanes != 15:
        for c in range(4):
            if not llanes & pista(c):
                w('        vu.m_state.vf[%d][%d] = oldLo[%d];' % (lreg, c, c))
    if up['accWrite'] not in (0, 15):
        for c in range(4):
            if not up['accWrite'] & pista(c):
                w('        vu.m_state.acc[%d] = oldAcc[%d];' % (c, c))
    if vi_escrito:
        w('        vu.m_state.vi[%d] = static_cast<int16_t>(vu.m_state.vi[%d]);' % (vi_escrito, vi_escrito))
    # markPairWrites
    if lreg != 0 and d['suppressed'] != lreg:
        lat = lo['vfLatency'] or lo['latency']
        for c in range(4):
            if llanes & pista(c):
                w('        vu.m_vfReady[%d][%d] = vu.m_cycle + %du;' % (lreg, c, lat))
    if ureg != 0:
        lat = up['vfLatency'] or up['latency']
        for c in range(4):
            if ulanes & pista(c):
                w('        vu.m_vfReady[%d][%d] = vu.m_cycle + %du;' % (ureg, c, lat))
    for reg in range(1, 16):
        if lo['viWrite'] & (1 << reg):
            w('        vu.m_viReady[%d] = vu.m_cycle + %du;' % (reg, lo['viLatency'] or lo['latency']))
    for c in range(4):
        if up['accWrite'] & pista(c):
            w('        vu.m_accReady[%d] = vu.m_cycle + VU1Interpreter::kAccForwardLatency;' % c)
    if vi_escrito and lo['delaysNextBranchRead']:
        w('        vu.recordViWriteForBranch(%d, oldVi);' % vi_escrito)
    w('    }')
    w('    vu.m_state.vf[0][0] = 0.0f; vu.m_state.vf[0][1] = 0.0f; vu.m_state.vf[0][2] = 0.0f; vu.m_state.vf[0][3] = 1.0f;')
    w('    vu.m_state.vi[0] = 0;')
    w('    vu.m_state.pc = 0x%xu + 8u >= c.codeSize ? 0u : 0x%xu;' % (pc, pc + 8))
    w('    if (vu.m_state.branchPending)')
    w('    {')
    w('        if (vu.m_state.branchDelay == 0u) { vu.m_state.pc = vu.m_state.branchTarget & vu.microAddressMask(); vu.m_state.branchPending = false; }')
    w('        else --vu.m_state.branchDelay;')
    w('    }')
    # Fim de programa (mesma ordem de passoPar).
    d_bit, t_bit = d['dBit'], d['tBit']
    w('    {')
    w('        const bool dHalt = %s;' % ('vu.m_state.dBitEnabled' if d_bit else 'false'))
    w('        const bool tHalt = %s;' % ('vu.m_state.tBitEnabled' if t_bit else 'false'))
    w('        const bool haltBit = dHalt || tHalt;')
    w('        const bool haltBranch = haltBit && %s;' % ('true' if lo['pipeline'] == BRANCH else 'false'))
    w('        bool fim = false;')
    w('        if (vu.m_state.haltAfterDelaySlot) { vu.m_state.stoppedByD = vu.m_pendingHaltD; vu.m_state.stoppedByT = vu.m_pendingHaltT; fim = true; }')
    w('        else if (vu.m_state.ebit) fim = true;')
    w('        else if (haltBit && !haltBranch) { vu.m_state.stoppedByD = dHalt; vu.m_state.stoppedByT = tHalt; fim = true; }')
    if d['eBit']:
        w('        else vu.m_state.ebit = true;')
    else:
        w('        else if (haltBranch) { vu.m_state.haltAfterDelaySlot = true; vu.m_pendingHaltD = dHalt; vu.m_pendingHaltT = tHalt; }')
    w('        avanca();' if ESPECIALIZAR and AVANCO_EMBUTIDO else '        vu.advanceOneCycle();')
    w('        ++c.pares;')
    w('        if (fim) return VU1Interpreter::PassoFim;')
    w('    }')


def ler_censo(pasta):
    versoes, entradas, pares, arestas = {}, collections.defaultdict(set), collections.defaultdict(dict), collections.defaultdict(set)
    for linha in open(os.path.join(pasta, 'ps2x_vu1_censo.txt')):
        p = linha.split()
        if p[0] == 'versao':
            versoes[p[1]] = int(p[3])
        elif p[0] == 'entrada':
            entradas[p[1]].add(int(p[2], 16))
        elif p[0] == 'par':
            pares[p[1]][int(p[2], 16)] = int(p[3])
        elif p[0] == 'aresta':
            arestas[p[1]].add((int(p[2], 16), int(p[3], 16)))
    return versoes, entradas, pares, arestas


def ler_decodificado(pasta, h):
    caminho = os.path.join(pasta, 'ps2x_vu1_decod_%s.txt' % h)
    if not os.path.exists(caminho):
        return None
    saida = {}
    for linha in open(caminho):
        pc, inicializador = linha.split(' ', 1)
        saida[int(pc, 16)] = inicializador.strip()
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pasta')
    ap.add_argument('saida')
    ap.add_argument('--minimo', type=float, default=0.5, help='%% minimo dos pares para traduzir uma versao')
    ap.add_argument('--sem-especializar', action='store_true', help='modo explicito chamando sempre execUpper/execLower')
    ap.add_argument('--avanco-embutido', action='store_true', help='embute advanceOneCycle em cada par (mais lento)')
    ap.add_argument('--modo', choices=('explicito', 'passo'), default='explicito',
                    help='explicito: tempo resolvido por par (padrao); passo: passoPar embutido com o par constante')
    a = ap.parse_args()

    global ESPECIALIZAR, AVANCO_EMBUTIDO
    ESPECIALIZAR = not a.sem_especializar
    AVANCO_EMBUTIDO = a.avanco_embutido
    versoes, entradas, pares, arestas = ler_censo(a.pasta)
    total = sum(versoes.values()) or 1
    escolhidas = []
    for h, n in sorted(versoes.items(), key=lambda x: -x[1]):
        if 100.0 * n / total < a.minimo:
            continue
        decod = ler_decodificado(a.pasta, h)
        if decod is None:
            print('versao %s sem ps2x_vu1_decod_*.txt; pulada' % h, file=sys.stderr)
            continue
        escolhidas.append((h, n, decod))

    out = []
    w = out.append
    w('// Gerado por tools/vu1_tradutor.py a partir de %s. Contem microcodigo do jogo: nao versionar.' % os.path.basename(os.path.abspath(a.pasta)))
    w('#include "runtime/ps2_vu1.h"')
    w('#include "runtime/ps2_memory.h"')
    w('#include "runtime/gs/gs_frontend.h"')
    w('#include "ps2_vu1_detail.h"')
    w('#include "ps2_vu1_passo.inl"')
    w('#include "ps2_vu1_traduzido.h"')
    w('#include <algorithm>')
    w('#include <cstring>')
    w('')
    w('#include <cmath>')
    w('#include <limits>')
    w('')
    w('namespace')
    w('{')
    w('    // Copias de VU1Interpreter::normalizeOperand, de vuFloatToInt (ps2_vu1_upper.cpp) e do teste do CLIP.')
    w('    inline float vuNorm(float value)')
    w('    {')
    w('        uint32_t bits = 0;')
    w('        std::memcpy(&bits, &value, sizeof(bits));')
    w('        const uint32_t exponent = (bits >> 23) & 0xFFu;')
    w('        if (exponent == 0u)')
    w('            bits &= 0x80000000u;')
    w('        else if (exponent == 0xFFu)')
    w('            bits = (bits & 0x80000000u) | 0x7F7FFFFFu;')
    w('        std::memcpy(&value, &bits, sizeof(value));')
    w('        return value;')
    w('    }')
    w('    inline int32_t vuFloatToInt(float value, float scale)')
    w('    {')
    w('        const double scaled = static_cast<double>(value) * static_cast<double>(scale);')
    w('        if (scaled >= static_cast<double>(std::numeric_limits<int32_t>::max()))')
    w('            return std::numeric_limits<int32_t>::max();')
    w('        if (scaled <= static_cast<double>(std::numeric_limits<int32_t>::min()))')
    w('            return std::numeric_limits<int32_t>::min();')
    w('        return static_cast<int32_t>(scaled);')
    w('    }')
    w('    inline uint32_t vuClip(const float *vs, float w)')
    w('    {')
    w('        uint32_t wBits = 0u;')
    w('        std::memcpy(&wBits, &w, sizeof(wBits));')
    w('        const int32_t limit = (wBits & 0x7F800000u) != 0u ? static_cast<int32_t>(wBits & 0x7FFFFFFFu) : 0x007FFFFF;')
    w('        const auto excede = [limit](float value, uint32_t signMask)')
    w('        {')
    w('            uint32_t bits = 0u;')
    w('            std::memcpy(&bits, &value, sizeof(bits));')
    w('            bits ^= signMask;')
    w('            int32_t ordered = 0;')
    w('            std::memcpy(&ordered, &bits, sizeof(ordered));')
    w('            return ordered > limit;')
    w('        };')
    w('        uint32_t flags = 0u;')
    w('        if (excede(vs[0], 0x00000000u)) flags |= 0x01u;')
    w('        if (excede(vs[0], 0x80000000u)) flags |= 0x02u;')
    w('        if (excede(vs[1], 0x00000000u)) flags |= 0x04u;')
    w('        if (excede(vs[1], 0x80000000u)) flags |= 0x08u;')
    w('        if (excede(vs[2], 0x00000000u)) flags |= 0x10u;')
    w('        if (excede(vs[2], 0x80000000u)) flags |= 0x20u;')
    w('        return flags;')
    w('    }')
    w('}')
    w('')
    w('#define P(n) static_cast<VU1Interpreter::Pipeline>(n)')
    w('#define PAR(D, PROXIMO) \\')
    w('    r = vu.passoPar(D, c.vuData, c.dataSize, *c.gs, c.memory, c.codeSize, c.budgetEnd); \\')
    w('    if (r != VU1Interpreter::PassoContinua) \\')
    w('    { \\')
    w('        c.pares += r == VU1Interpreter::PassoFim ? 1u : 0u; \\')
    w('        return r; \\')
    w('    } \\')
    w('    ++c.pares; \\')
    w('    if (vu.m_state.pc != (PROXIMO)) \\')
    w('        goto despacho;')
    w('')
    total_pares = 0
    palavras = []
    for indice, (h, n, decod) in enumerate(escolhidas):
        executados = sorted(pc for pc in pares[h] if pc in decod and not campos(decod[pc])['lo']['reserved'] and not campos(decod[pc])['up']['reserved'])
        conjunto = set(executados)
        lideres = set(entradas[h])
        for (o, d) in arestas[h]:
            lideres.add(d)
            lideres.add(o + 8)
        lideres &= conjunto
        # Todo par executado precisa estar em algum bloco: comeca um bloco onde o anterior nao foi executado.
        for pc in executados:
            if pc - 8 not in conjunto:
                lideres.add(pc)
        total_pares += len(executados)
        palavras.append([(pc, campos(decod[pc])['lower'], campos(decod[pc])['upper']) for pc in executados])
        w('// versao %s: %.1f%% dos pares do censo, %d pares executados, %d blocos' % (h, 100.0 * n / total, len(executados), len(lideres)))
        w('template <>')
        w('int Vu1Traduzido::versao<%d>(VU1Interpreter &vu, Contexto &c)' % indice)
        w('{')
        if a.modo == 'passo':
            for pc in executados:
                w('    static constexpr VU1Interpreter::DecodedInstructionPair d_%x = %s;' % (pc, decod[pc]))
        if a.modo == 'explicito' and ESPECIALIZAR:
            for linha in vu1_instrucoes.lambdas_versao():
                w(linha)
        w('    int r = VU1Interpreter::PassoContinua;')
        w('    (void)r;')
        w('despacho:')
        w('    switch (vu.m_state.pc)')
        w('    {')
        # Entrada em qualquer par executado: o orcamento de ciclos pode acabar no meio de um bloco, e a proxima chamada
        # recomeca ali.
        for pc in executados:
            w('    case 0x%x:' % pc)
            w('        goto l_%x;' % pc)
        w('    default:')
        w('        return VU1Interpreter::PassoContinua;')
        w('    }')
        for pc in executados:
            w('l_%x:' % pc)
            if a.modo == 'passo':
                w('    PAR(d_%x, 0x%xu)' % (pc, pc + 8))
            else:
                gera_par(pc, campos(decod[pc]), w)
                w('    if (vu.m_state.pc != 0x%xu) goto despacho;' % (pc + 8))
            if pc + 8 not in conjunto:
                w('    goto despacho;')
        w('}')
        w('')
        w('static const Vu1Traduzido::Bloco g_tabela%d[2048] = {' % indice)
        linha = []
        for i in range(2048):
            linha.append('&Vu1Traduzido::versao<%d>' % indice if i * 8 in conjunto else 'nullptr')
            if len(linha) == 8:
                w('    ' + ', '.join(linha) + ',')
                linha = []
        w('};')
        w('')
    w('#undef PAR')
    w('#undef P')
    w('')
    w('const Vu1Traduzido::Bloco *Vu1Traduzido::tabelaPorHash(uint64_t hash)')
    w('{')
    w('    switch (hash)')
    w('    {')
    for indice, (h, n, decod) in enumerate(escolhidas):
        w('    case 0x%sull:' % h)
        w('        return g_tabela%d;' % indice)
    w('    default:')
    w('        return nullptr;')
    w('    }')
    w('}')
    w('')
    w('namespace')
    w('{')
    w('    struct ParConferido')
    w('    {')
    w('        uint32_t pc, lower, upper;')
    w('    };')
    for indice, (h, n, decod) in enumerate(escolhidas):
        lista = palavras[indice]
        w('    const ParConferido g_pares%d[%d] = {' % (indice, len(lista)))
        for i in range(0, len(lista), 4):
            w('        ' + ' '.join('{0x%x, 0x%08xu, 0x%08xu},' % t for t in lista[i:i + 4]))
        w('    };')
    w('')
    w('    bool confere(const ParConferido *pares, size_t n, const uint8_t *codigo, uint32_t tamanho)')
    w('    {')
    w('        for (size_t i = 0; i < n; ++i)')
    w('        {')
    w('            if (pares[i].pc + 8u > tamanho)')
    w('                return false;')
    w('            uint32_t palavras[2];')
    w('            std::memcpy(palavras, codigo + pares[i].pc, sizeof(palavras));')
    w('            if (palavras[0] != pares[i].lower || palavras[1] != pares[i].upper)')
    w('                return false;')
    w('        }')
    w('        return true;')
    w('    }')
    w('}')
    w('')
    w('const Vu1Traduzido::Bloco *Vu1Traduzido::tabelaPorConteudo(const uint8_t *codigo, uint32_t tamanho)')
    w('{')
    for indice in range(len(escolhidas)):
        w('    if (confere(g_pares%d, %d, codigo, tamanho))' % (indice, len(palavras[indice])))
        w('        return g_tabela%d;' % indice)
    w('    return nullptr;')
    w('}')
    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    with open(a.saida, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('%d versoes, %d pares traduzidos -> %s' % (len(escolhidas), total_pares, a.saida))
    if a.modo == 'explicito':
        print('instrucoes geradas direto: superiores %d de %d, inferiores %d de %d (o resto chama o interpretador)' %
              (CONTAGEM['sup'], CONTAGEM['sup_total'], CONTAGEM['inf'], CONTAGEM['inf_total']))


if __name__ == '__main__':
    main()
