#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/in.h>
#include <linux/ip.h>
#include <linux/pkt_cls.h>
#include <linux/udp.h>

#include "../include/gtpu.h"

/* Minimal helpers/macros to keep this standalone for tc clang builds */
#define SEC(NAME) __attribute__((section(NAME), used))
#define __uint(name, val) int (*name)[val]
#define __type(name, val) val *name

static void *(*bpf_map_lookup_elem)(void *map, const void *key) = (void *)BPF_FUNC_map_lookup_elem;
static long (*bpf_map_update_elem)(void *map, const void *key, const void *value, __u64 flags) = (void *)BPF_FUNC_map_update_elem;

static __always_inline __u16 bpf_ntohs(__u16 x)
{
    return __builtin_bswap16(x);
}

static __always_inline __u32 bpf_ntohl(__u32 x)
{
    return __builtin_bswap32(x);
}

enum stat_index {
    STAT_GTPU_PKTS = 0,
    STAT_GTPU_BYTES = 1,
    STAT_MALFORMED = 2,
    STAT_NON_GTPU = 3,
    STAT_MAX = 4,
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, STAT_MAX);
    __type(key, __u32);
    __type(value, __u64);
} global_stats SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, __u32);   /* TEID in host order */
    __type(value, __u64); /* packet counters */
} teid_pkt_cnt SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, __u32);   /* TEID in host order */
    __type(value, __u64); /* byte counters */
} teid_byte_cnt SEC(".maps");

struct gtpu_last_seen {
    __u32 outer_src;
    __u32 outer_dst;
    __u16 udp_src;
    __u16 udp_dst;
    __u8 msg_type;
    __u8 pad1;
    __u16 pad2;
    __u32 last_pkt_len;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, __u32); /* TEID in host order */
    __type(value, struct gtpu_last_seen);
} teid_last_seen SEC(".maps");

static __always_inline void incr_array_counter(__u32 idx, __u64 delta)
{
    __u64 *v = bpf_map_lookup_elem(&global_stats, &idx);
    if (v)
        __sync_fetch_and_add(v, delta);
}

static __always_inline void incr_teid_counter(void *map, __u32 teid, __u64 delta)
{
    __u64 *v = bpf_map_lookup_elem(map, &teid);
    if (v) {
        __sync_fetch_and_add(v, delta);
        return;
    }

    __u64 init = delta;
    bpf_map_update_elem(map, &teid, &init, BPF_ANY);
}

SEC("classifier")
int tc_gtpu_ingress(struct __sk_buff *skb)
{
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_OK;

    if (bpf_ntohs(eth->h_proto) != ETH_P_IP) {
        incr_array_counter(STAT_NON_GTPU, 1);
        return TC_ACT_OK;
    }

    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) {
        incr_array_counter(STAT_MALFORMED, 1);
        return TC_ACT_OK;
    }

    if (iph->version != 4 || iph->ihl < 5) {
        incr_array_counter(STAT_MALFORMED, 1);
        return TC_ACT_OK;
    }

    if (iph->protocol != IPPROTO_UDP) {
        incr_array_counter(STAT_NON_GTPU, 1);
        return TC_ACT_OK;
    }

    __u32 ip_hdr_len = (__u32)iph->ihl * 4;
    struct udphdr *udph = (void *)iph + ip_hdr_len;
    if ((void *)(udph + 1) > data_end) {
        incr_array_counter(STAT_MALFORMED, 1);
        return TC_ACT_OK;
    }

    __u16 sport = bpf_ntohs(udph->source);
    __u16 dport = bpf_ntohs(udph->dest);
    if (sport != GTPU_PORT && dport != GTPU_PORT) {
        incr_array_counter(STAT_NON_GTPU, 1);
        return TC_ACT_OK;
    }

    struct gtpu_v1_hdr *gtp = (void *)(udph + 1);
    if ((void *)(gtp + 1) > data_end) {
        incr_array_counter(STAT_MALFORMED, 1);
        return TC_ACT_OK;
    }

    __u32 teid = bpf_ntohl(gtp->teid);
    __u32 pkt_len = (__u32)(data_end - data);

    incr_array_counter(STAT_GTPU_PKTS, 1);
    incr_array_counter(STAT_GTPU_BYTES, pkt_len);
    incr_teid_counter(&teid_pkt_cnt, teid, 1);
    incr_teid_counter(&teid_byte_cnt, teid, pkt_len);

    struct gtpu_last_seen ls = {
        .outer_src = bpf_ntohl(iph->saddr),
        .outer_dst = bpf_ntohl(iph->daddr),
        .udp_src = sport,
        .udp_dst = dport,
        .msg_type = gtp->msg_type,
        .last_pkt_len = pkt_len,
    };
    bpf_map_update_elem(&teid_last_seen, &teid, &ls, BPF_ANY);

    return TC_ACT_OK;
}

char __license[] SEC("license") = "GPL";
