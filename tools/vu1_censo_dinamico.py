"""censo_vu1.py pasta: resume ps2x_vu1_censo.txt (versoes do codigo do VU1, entradas, blocos quentes, alvos de JR/JALR)."""
import collections
import os
import struct
import sys

pasta = sys.argv[1]
versoes = {}
entradas = collections.defaultdict(dict)
pares = collections.defaultdict(dict)
arestas = collections.defaultdict(dict)
for l in open(os.path.join(pasta, 'ps2x_vu1_censo.txt')):
    p = l.split()
    if p[0] == 'versao':
        versoes[p[1]] = (int(p[3]), int(p[5]))
    elif p[0] == 'entrada':
        entradas[p[1]][int(p[2], 16)] = int(p[3])
    elif p[0] == 'par':
        pares[p[1]][int(p[2], 16)] = int(p[3])
    elif p[0] == 'aresta':
        arestas[p[1]][(int(p[2], 16), int(p[3], 16))] = int(p[4])

NOMES = {0x20: 'B', 0x21: 'BAL', 0x24: 'JR', 0x25: 'JALR', 0x28: 'IBEQ', 0x29: 'IBNE', 0x2C: 'IBLTZ',
         0x2D: 'IBGTZ', 0x2E: 'IBLEZ', 0x2F: 'IBGEZ'}

total = sum(v[0] for v in versoes.values())
print('versoes=%d pares=%d' % (len(versoes), total))
acum = 0
for h, (n, ch) in sorted(versoes.items(), key=lambda x: -x[1][0]):
    acum += n
    if n * 200 < total:
        continue
    codigo = open(os.path.join(pasta, 'ps2x_vu1_codigo_%s.bin' % h), 'rb').read()
    inferior = lambda pc: struct.unpack_from('<I', codigo, pc)[0]
    ops = lambda pc: inferior(pc) >> 25
    executados = pares[h]
    # Lideres: entradas, destinos de desvio e o par depois de cada origem de desvio (fim do delay slot).
    lideres = set(entradas[h])
    for (o, d) in arestas[h]:
        lideres.add(d)
        lideres.add(o + 8)
    for pc in executados:
        op = ops(pc)
        if op in NOMES:
            lideres.add(pc + 16)
    blocos = []
    for lid in sorted(lideres):
        if lid not in executados:
            continue
        fim = lid
        while fim + 8 in executados and fim + 8 not in lideres:
            fim += 8
        blocos.append((sum(executados[x] for x in range(lid, fim + 8, 8)), lid, fim, executados[lid]))
    blocos.sort(reverse=True)
    print('\n== versao %s: %.1f%% dos pares (acum %.1f%%), chamadas=%d, pares distintos=%d, blocos=%d' %
          (h, 100 * n / total, 100 * acum / total, ch, len(executados), len(blocos)))
    print('  entradas:', ', '.join('%x(%d)' % e for e in sorted(entradas[h].items(), key=lambda x: -x[1])[:8]))
    q = 0
    for peso, lid, fim, vezes in blocos[:12]:
        q += peso
        print('  bloco %4x-%4x %3d pares, %5.1f%% da versao (%d entradas, %.1f pares/entrada)' %
              (lid, fim, (fim - lid) // 8 + 1, 100 * peso / n, vezes, peso / max(vezes, 1)))
    print('  12 blocos mais quentes = %.1f%% da versao' % (100 * q / n))
    indiretos = collections.defaultdict(set)
    for (o, d), c in arestas[h].items():
        br = o - 8
        if br >= 0 and ops(br) in (0x24, 0x25):
            indiretos[br].add(d)
    if indiretos:
        print('  JR/JALR:', '; '.join('%x->{%s}' % (o, ','.join('%x' % d for d in sorted(ds))) for o, ds in sorted(indiretos.items())))
    usados = collections.Counter(NOMES.get(ops(pc), None) for pc in executados)
    usados.pop(None, None)
    print('  desvios executados:', dict(usados))
