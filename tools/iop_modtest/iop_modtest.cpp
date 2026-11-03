// Carrega os modulos IRX do disco (pasta extraida) no emulador de IOP do PS2Recomp e
// relata o resultado de cada um. Uso: iop_modtest <pasta com MODULES\> [modulo ...]
#include "ps2x/iop/iop_subsystem.h"
#include "ps2x/iop/iop_sreg.h"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using namespace ps2x::iop;

static std::string lower(std::string s)
{
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

class TestHost final : public IopHost
{
public:
    explicit TestHost(fs::path root) : root_(std::move(root)), guest_(32u << 20, 0u) {}

    bool readGuest(uint32_t a, void *d, size_t n) const override
    {
        if (a > guest_.size() || n > guest_.size() - a) return false;
        std::memcpy(d, guest_.data() + a, n);
        return true;
    }
    bool writeGuest(uint32_t a, const void *s, size_t n) override
    {
        if (a > guest_.size() || n > guest_.size() - a) return false;
        std::memcpy(guest_.data() + a, s, n);
        return true;
    }
    bool zeroGuest(uint32_t a, size_t n) override
    {
        if (a > guest_.size() || n > guest_.size() - a) return false;
        std::fill_n(guest_.begin() + a, n, uint8_t{0});
        return true;
    }
    bool normalizeGuestAddress(uint32_t a, uint32_t &o) const override { o = a; return a < guest_.size(); }
    uint32_t allocateIopHandle(IopHandleKind) override { return next_ += 0x80u; }
    uint32_t allocateGuest(uint32_t, uint32_t) override { return 0u; }
    void freeGuest(uint32_t) override {}
    void audioCommand(uint32_t, uint32_t, GuestBuffer, GuestBuffer) override {}
    std::string hostPath(HostPathKind k) const override { return k == HostPathKind::CdRoot ? root_.string() : std::string(); }

    // "cdrom0:\MODULES\X.IRX;1" -> <root>/MODULES/X.IRX (sem diferenciar maiusculas)
    std::string translateGuestPath(std::string_view p) const override
    {
        std::string s(p);
        if (auto c = s.find(':'); c != std::string::npos) s = s.substr(c + 1);
        if (auto v = s.find(';'); v != std::string::npos) s = s.substr(0, v);
        std::replace(s.begin(), s.end(), '\\', '/');
        while (!s.empty() && s.front() == '/') s.erase(s.begin());
        fs::path cur = root_;
        size_t pos = 0;
        while (pos <= s.size())
        {
            size_t e = s.find('/', pos);
            std::string part = s.substr(pos, e == std::string::npos ? std::string::npos : e - pos);
            if (!part.empty())
            {
                fs::path found;
                std::error_code ec;
                for (auto &ent : fs::directory_iterator(cur, ec))
                    if (lower(ent.path().filename().string()) == lower(part)) { found = ent.path(); break; }
                if (found.empty()) return {};
                cur = found;
            }
            if (e == std::string::npos) break;
            pos = e + 1;
        }
        return cur.string();
    }
    uint64_t openHostFile(std::string_view p) override
    {
        std::ifstream f(std::string(p), std::ios::binary);
        if (!f) return 0u;
        std::vector<uint8_t> b((std::istreambuf_iterator<char>(f)), {});
        files_[++handle_] = std::move(b);
        return handle_;
    }
    bool hostFileSize(uint64_t h, uint64_t &s) const override
    {
        auto it = files_.find(h);
        if (it == files_.end()) return false;
        s = it->second.size();
        return true;
    }
    bool readHostFile(uint64_t h, uint64_t off, void *d, size_t n, size_t &r) override
    {
        r = 0;
        auto it = files_.find(h);
        if (it == files_.end() || off > it->second.size()) return false;
        r = std::min(n, it->second.size() - static_cast<size_t>(off));
        std::memcpy(d, it->second.data() + off, r);
        return true;
    }
    void closeHostFile(uint64_t h) override { files_.erase(h); }
    int32_t memoryCard(const MemoryCardRequest &) override { return -1; }
    bool hasGuestFunction(uint32_t) const override { return false; }
    bool invokeGuestFunction(uint64_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t *) override { return false; }
    void log(LogLevel l, std::string_view m) override
    {
        static const char *n[] = {"DEBUG", "INFO", "WARN", "ERROR"};
        if (l >= LogLevel::Info || verbose) std::cout << "    [" << n[static_cast<int>(l)] << "] " << m << "\n";
    }
    bool sendSifCommand(uint32_t id, const void *pkt, size_t n) override
    {
        const uint32_t *w = static_cast<const uint32_t *>(pkt);
        std::cout << "    [IOP->EE cmd] cid=0x" << std::hex << id << std::dec << " size=" << n << " data:";
        for (size_t i = 4; i < n / 4 && i < 12; ++i) std::cout << " 0x" << std::hex << w[i];
        std::cout << std::dec << "\n";
        return true;
    }
    bool verbose = false;

private:
    fs::path root_;
    std::vector<uint8_t> guest_;
    uint32_t next_ = 0x1000u;
    uint64_t handle_ = 0u;
    std::map<uint64_t, std::vector<uint8_t>> files_;
};

int main(int argc, char **argv)
{
    if (argc < 2) { std::cerr << "uso: iop_modtest <pasta do disco> [modulo ...]\n"; return 2; }
    TestHost host(argv[1]);
    for (int i = 2; i < argc; ++i)
        if (std::string(argv[i]) == "-v") host.verbose = true;
    std::vector<std::string> mods;
    for (int i = 2; i < argc; ++i)
        if (std::string(argv[i]) != "-v") mods.push_back(argv[i]);
    if (mods.empty())
        mods = {"SIO2MAN.IRX", "SIO2D.IRX", "DS2U_D.IRX", "MCMAN.IRX", "MCSERV.IRX",
                "LIBSD.IRX", "AUDIOPF.IRX", "DBCMAN.IRX"};

    IopSubsystem iop(host);
    iop.reset();
    int fails = 0;
    for (const auto &m : mods)
    {
        const std::string path = "cdrom0:\\MODULES\\" + m + ";1";
        std::cout << "== " << m << "\n";
        const auto r = iop.loadModule(path);
        std::cout << "   handled=" << r.handled << " moduleId=" << r.moduleId << " startResult=" << r.startResult << "\n";
        if (r.moduleId <= 0) ++fails;
    }
    // Simula o EE: entrega SET_SREG(0x1f/0x1e) e deixa o IOP rodar um tempo
    ps2x::iop::iopSifSregSet(0x1f, 0x403b40);
    ps2x::iop::iopSifSregSet(0x1e, 0x40bb40);
    for (int i = 0; i < 400; ++i) iop.runEeCycles(4000000);
    const auto snap = iop.debugSnapshot();
    std::cout << "\nemulador: modulos=" << snap.emulatorLoadedModules << " threads=" << snap.emulatorThreads
              << " servidores RPC=" << snap.emulatorRpcServers << " instrucoes=" << snap.emulatorInstructions << "\n";
    for (const auto &s : snap.services) std::cout << "servico HLE: " << s.name << "\n";
    for (const auto &d : snap.diagnostics) std::cout << "diag: " << d << "\n";
    std::cout << "falhas de carga: " << fails << "/" << mods.size() << "\n";
    return fails ? 1 : 0;
}
