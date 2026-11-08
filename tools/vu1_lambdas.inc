    // Copia de VU1Interpreter::updateFmacFlags (ps2_vu1_core.cpp), para o FMAC traduzido.
    const auto flagsFmac = [&](const uint8_t laneFlags[4], uint8_t dest, uint32_t extraSticky) __attribute__((always_inline))
    {
        uint32_t mac = 0u;
        uint32_t status = 0u;
        for (uint32_t component = 0; component < 4u; ++component)
        {
            const uint8_t lane = static_cast<uint8_t>(1u << (3u - component));
            if ((dest & lane) == 0u)
                continue;
            const uint32_t flags = laneFlags[component];
            if ((flags & 0x1u) != 0u)
                mac |= lane;
            if ((flags & 0x2u) != 0u)
                mac |= static_cast<uint32_t>(lane) << 4;
            if ((flags & 0x4u) != 0u)
                mac |= static_cast<uint32_t>(lane) << 8;
            if ((flags & 0x8u) != 0u)
                mac |= static_cast<uint32_t>(lane) << 12;
            status |= flags;
        }
        VU1Interpreter::FlagPipelineEntry *entry = nullptr;
        for (VU1Interpreter::FlagPipelineEntry &candidate : vu.m_flagPipeline)
        {
            if (!candidate.valid)
            {
                entry = &candidate;
                break;
            }
        }
        if (!entry)
        {
            vu.reportReservedInstruction(true, 0xFFFFFFFFu);
            return;
        }
        *entry = {};
        entry->valid = true;
        g_ps2xMascarasPipeline[1].flag |= 1u << static_cast<uint32_t>(entry - vu.m_flagPipeline.data());
        entry->issueCycle = vu.m_cycle;
        entry->readyCycle = vu.m_cycle + VU1Interpreter::kFmacLatency;
        entry->mac = mac;
        entry->status = status;
        entry->extraSticky = extraSticky;
        entry->writesMac = true;
        entry->writesStatus = true;
    };
    // Copia de advanceOneCycle + commitReadyPipelines (mesma ordem: flags, Q, P, stores; VF/VI/ACC pelo original).
    const auto avanca = [&]() __attribute__((always_inline))
    {
        ++vu.m_cycle;
        vu.m_state.cycles = vu.m_cycle;
        Ps2xMascarasPipeline &ativas = g_ps2xMascarasPipeline[1];
        for (uint32_t bits = ativas.flag; bits != 0u; bits &= bits - 1u)
        {
            const uint32_t indice = static_cast<uint32_t>(__builtin_ctz(bits));
            VU1Interpreter::FlagPipelineEntry &entry = vu.m_flagPipeline[indice];
            if (entry.readyCycle > vu.m_cycle)
                continue;
            if (entry.writesMac)
                vu.m_state.mac = entry.mac;
            if (entry.writesStatus)
            {
                const uint32_t current = entry.status & 0xFu;
                vu.m_state.status = (vu.m_state.status & 0xFF0u) | current | ((current | entry.extraSticky) << 6);
            }
            if (entry.writesSticky)
                vu.m_state.status = (vu.m_state.status & 0x03Fu) | (entry.status & 0xFC0u);
            if (entry.writesClip)
                vu.m_state.clip = entry.clip;
            entry.valid = false;
            ativas.flag &= ~(1u << indice);
        }
        if (vu.m_fdiv.valid && vu.m_fdiv.readyCycle <= vu.m_cycle)
        {
            vu.m_state.q = vu.m_fdiv.value;
            const uint32_t currentDi = vu.m_fdiv.statusDi & 0x30u;
            vu.m_state.status = (vu.m_state.status & 0xFCFu) | currentDi | (currentDi << 6);
            vu.m_fdiv = {};
        }
        for (VU1Interpreter::ScalarPipelineEntry &entry : vu.m_efu)
        {
            if (entry.valid && entry.readyCycle <= vu.m_cycle)
            {
                vu.m_state.p = entry.value;
                entry = {};
            }
        }
        for (uint32_t bits = ativas.store; bits != 0u; bits &= bits - 1u)
        {
            const uint32_t indice = static_cast<uint32_t>(__builtin_ctz(bits));
            VU1Interpreter::PendingStore &store = vu.m_storePipeline[indice];
            if (store.readyCycle > vu.m_cycle)
                continue;
            if (vu.m_activeVuData && store.address + 16u <= vu.m_activeVuDataSize)
            {
                uint32_t oldWords[4]{};
                std::memcpy(oldWords, vu.m_activeVuData + store.address, sizeof(oldWords));
                for (uint32_t component = 0; component < 4u; ++component)
                {
                    if ((store.laneMask & (1u << (3u - component))) != 0u)
                        oldWords[component] = store.words[component];
                }
                std::memcpy(vu.m_activeVuData + store.address, oldWords, sizeof(oldWords));
            }
            store.valid = false;
            ativas.store &= ~(1u << indice);
        }
        if ((ativas.vf | ativas.vi | ativas.acc) != 0u)
            vu.commitReadyPipelines();
        if (vu.m_xgkick.active)
            vu.progressXgkick();
    };
    (void)flagsFmac;
    (void)avanca;
