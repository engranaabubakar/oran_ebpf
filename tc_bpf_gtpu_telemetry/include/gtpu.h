#ifndef __GTPU_H__
#define __GTPU_H__

#include <linux/types.h>

#define GTPU_PORT 2152

/* Minimal GTP-U v1 header (8 bytes base) */
struct gtpu_v1_hdr {
    __u8 flags;
    __u8 msg_type;
    __be16 length;
    __be32 teid;
} __attribute__((packed));

/* GTP-U flags bits for optional fields */
#define GTPU_FLAG_E 0x04
#define GTPU_FLAG_S 0x02
#define GTPU_FLAG_PN 0x01

#endif
