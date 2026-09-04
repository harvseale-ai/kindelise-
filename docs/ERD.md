# Kindelise Entity Relationship Diagram

```mermaid
erDiagram
    DJANGO_USER ||--o| PROFILE : owns
    PROFILE }o--o{ INTEREST : selects

    DJANGO_USER ||--o{ PLAN : creates
    DJANGO_USER ||--o{ PARTICIPATION : joins
    PLAN ||--o{ PARTICIPATION : has
    PLAN ||--o| PLAN_CHAT : opens
    PLAN_CHAT ||--o{ PLAN_CHAT_MESSAGE : contains
    DJANGO_USER ||--o{ PLAN_CHAT_MESSAGE : sends

    DJANGO_USER ||--o{ CONVERSATION : first_member
    DJANGO_USER ||--o{ CONVERSATION : second_member
    CONVERSATION ||--o{ MESSAGE : contains
    DJANGO_USER ||--o{ MESSAGE : sends

    DJANGO_USER ||--o{ NOTIFICATION : receives
    MESSAGE o|--o{ NOTIFICATION : creates
    PARTICIPATION o|--o{ NOTIFICATION : creates
    PLAN_CHAT_MESSAGE o|--o{ NOTIFICATION : creates

    DJANGO_USER ||--o{ BLOCK : blocks
    DJANGO_USER ||--o{ BLOCK : is_blocked

    DJANGO_USER ||--o{ REPORT : submits
    DJANGO_USER ||--o{ REPORT : is_reported
    PLAN o|--o{ REPORT : may_explain
    CONVERSATION o|--o{ REPORT : may_explain
    MESSAGE o|--o{ REPORT : may_explain
    PLAN_CHAT_MESSAGE o|--o{ REPORT : may_explain

    DJANGO_USER ||--o| PLATFORM_SUBSCRIPTION : owns

    DJANGO_USER {
        int id PK
        string email
        boolean is_active
        boolean is_staff
    }

    PROFILE {
        int id PK
        int user_id FK
        string display_name
        string broad_areas
        datetime available_from
        boolean is_verified
    }

    INTEREST {
        int id PK
        string name UK
    }

    PLAN {
        int id PK
        int owner_id FK
        string title
        string public_place
        string public_address
        datetime starts_at
        int capacity
        string status
    }

    PARTICIPATION {
        int id PK
        int plan_id FK
        int user_id FK
        string status
        datetime requested_at
        datetime joined_at
        datetime decided_at
        datetime left_at
    }

    PLAN_CHAT {
        int id PK
        int plan_id FK, UK
        datetime updated_at
    }

    PLAN_CHAT_MESSAGE {
        int id PK
        int chat_id FK
        int sender_id FK
        string body
        datetime sent_at
    }

    CONVERSATION {
        int id PK
        int first_user_id FK
        int second_user_id FK
        datetime updated_at
    }

    MESSAGE {
        int id PK
        int conversation_id FK
        int sender_id FK
        string body
        datetime sent_at
    }

    NOTIFICATION {
        int id PK
        int recipient_id FK
        int message_id FK
        int participation_id FK
        int plan_chat_message_id FK
        string kind
        datetime read_at
    }

    BLOCK {
        int id PK
        int blocker_id FK
        int blocked_user_id FK
    }

    REPORT {
        int id PK
        int reporter_id FK
        int reported_user_id FK
        int reported_plan_chat_message_id FK
        string category
        string status
    }

    PLATFORM_SUBSCRIPTION {
        int id PK
        int user_id FK
        string stripe_status
        datetime access_until
    }

    STRIPE_WEBHOOK_RECEIPT {
        int id PK
        string stripe_event_id UK
        string event_type
        datetime processed_at
    }
```

## Relationship summary

| Relationship | Meaning |
| --- | --- |
| User → Profile | Every normal account has one public profile. |
| Profile ↔ Interest | A profile can select several interests, and an interest can belong to several profiles. |
| User → Plan | A user can create several plans. |
| User ↔ Plan | `Participation` preserves pending, confirmed, declined and left membership states. |
| Plan → Plan Chat | The owner and confirmed participants share one plan-specific conversation. |
| Conversation → Message | One private conversation contains messages from its two members. |
| Notification | Direct messages, plan-chat messages and participation changes can create alerts. |
| Block and Report | These records store private safety actions and checked message context. |
| Platform Subscription | An account can have one locally stored Stripe subscription summary. |
| Stripe Webhook Receipt | Stores processed Stripe event IDs to prevent duplicate processing. |

`PK` means primary key, `FK` means foreign key, and `UK` means unique value.
