# RFC-005: Social Media and Real-Time Communications Engine

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Target Audience:** Engineering, Social & Growth, Security Teams  
> **Depends On:** RFC-001 (IAM), RFC-003 (Frontend Shell)

---

## 1. Abstract

This RFC defines the architecture for the **Social Media and Communications Engine** — the engagement layer of the Super App. It specifies a hybrid data strategy using Graph Databases for social connections and Distributed NoSQL for feed persistence, a secure real-time messaging system with End-to-End Encryption (E2EE), and a global media delivery pipeline for user-generated content (UGC).

---

## 2. Social Graph & Data Architecture

To handle millions of user connections and facilitate sub-second "Friend-of-Friend" queries, the Super App adopts a partitioned graph strategy.

### 2.1. Graph Database: Neo4j Aura (Global)
**Justification:** Relational databases (SQL) and simple NoSQL (Cassandra) fail at deep relationship traverses (e.g., "Find all restaurants liked by friends of my friends"). 
- **Neo4j** is used for the **Social Graph** (relationships, follows, blocks, group memberships).
- **Cassandra/ScyllaDB** is used for the **Activity Feed** (post content, metadata, timelines).

**Neo4j Schema Design:**
```cypher
// Create User Node
CREATE (:User {id: "usr_123", region: "INDIA", name: "Raj"});

// Create Relationship (directed)
MATCH (a:User {id: "usr_123"}), (b:User {id: "usr_456"})
CREATE (a)-[:FOLLOWS {since: timestamp()}]->(b);

// Query: Personalized Recommendations
MATCH (me:User {id: "usr_123"})-[:FOLLOWS]->(friend)-[:LIKES]->(restaurant:Service)
WHERE NOT (me)-[:LIKES]->(restaurant)
RETURN restaurant.name, count(*) AS strength
ORDER BY strength DESC LIMIT 10;
```

### 2.2. Distributed NoSQL (Activity Store)
All posts, comments, and reactions are stored in **Cassandra** to ensure high write availability and regional partitioning.
- **Partition Key:** `user_id` + `bucket_id` (time-based)
- **Clustering Key:** `created_at` (descending)

---

## 3. Real-Time Messaging & E2EE

The messaging engine must be as reliable as WhatsApp and as secure as Signal.

### 3.1. Signaling & WebSockets
- **Transport**: Secure WebSockets (`wss://`) managed by a dedicated **Messaging Gateway**.
- **Orchestration**: **RabbitMQ** (for low-latency queueing) or **Kafka** (for message durability/replay).
- **Presence**: Redis-backed presence tracking (Online/Away/Offline).

### 3.2. End-to-End Encryption (Signal Protocol)
All private chats use the **Signal Protocol** (Triple Diffie-Hellman + Double Ratchet).
1. **Key Bundles**: Users upload Identity Keys and One-Time Pre-keys to the **Keyserver** during registration.
2. **Handshake**: The sender fetches the recipient's bundle to establish a shared secret.
3. **Encryption**: Content is encrypted on-device. The Super App backend only sees encrypted blobs (`X3DH` envelopes).
4. **Residency**: Encrypted message blobs are stored in the recipient's home region (e.g., Mumbai for India users) until delivered, then marked for deletion or archival per regional laws.

---

## 4. Media Delivery & Storage (UGC)

### 4.1. The Upload Pipeline
1. **Direct-to-S3**: Clients request a pre-signed S3 URL from the **Media Service**.
2. **Edge Transcoding**: AWS Lambda @ Edge triggers upon upload:
   - **Compression**: WebP for images, H.265/HEVC for video.
   - **Moderation**: Amazon Rekognition / Google Vision AI scan for prohibited content (CSAM, violence).
3. **Compliance**: Media is pinned to the uploader's region (GDPR/RBI) and distributed via **CloudFront** with Geo-restrictions.

---

## 5. API Contracts: GraphQL Social Schema

To allow the shell to query complex, nested feed data in a single round-trip, a GraphQL interface is exposed via the **Social Gateway**.

```graphql
# social_schema.graphql

type User {
  id: ID!
  displayName: String!
  avatarUrl: String
  connectionStatus: SocialStatus
}

type Post {
  id: ID!
  author: User!
  content: String!
  media: [MediaAsset]
  reactions: [ReactionSummary]
  comments(limit: Int): [Comment]
  createdAt: Float!
  region: String!
}

type Feed {
  items: [Post]
  nextCursor: String
  adverts: [SponsoredContent]
}

type Query {
  # Personalized, algorithmically sorted feed
  getFeed(limit: Int, cursor: String, filter: FeedFilter): Feed
  
  # Search friends and public figures
  searchPeople(query: String!): [User]
}

enum SocialStatus {
  NONE
  FOLLOWING
  BLOCKED
  MUTUAL
}
```

---

## 6. Execution Tasks (Epic 5 Extension)

| Task ID | Component | Description |
|---|---|---|
| S-101 | **Social Graph** | Deploy Neo4j Cluster and implement Follow/Unfollow logic. |
| S-102 | **Messaging** | Implement WebSocket Gateway with Signal Protocol handshake. |
| S-103 | **UGC Pipeline** | Setup S3 event-driven transcoding and moderation workers. |
| S-104 | **Feed Engine** | Implement GraphQL Aggregator to combine Cassandra + Neo4j data. |

*End of RFC-005*
