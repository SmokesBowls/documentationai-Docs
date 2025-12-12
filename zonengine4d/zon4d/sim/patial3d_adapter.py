┌─────────────────────────────────────────────────────────┐
│                    ZON4D Runtime Loop                    │
│                                                         │
│  ┌─────────────┐  Deltas  ┌──────────────────────┐     │
│  │ TaskRouter  ├─────────►│Spatial3DStateView    │     │
│  │             │          │ Adapter              │     │
│  └─────────────┘          │                      │     │
│                           │  • Validates AP      │     │
│                           │  • Queues deltas     │     │
│  ┌─────────────┐ Alerts   │  • Calls mr's kernel │     │
│  │ AP Validator│◄─────────┘                      │     │
│  │             │          └──────────┬───────────┘     │
│  └─────────────┘                     │                 │
│                           Physics Step│                 │
└───────────────────────────────────────┼─────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────┐
│              mr's Functional Physics Kernel              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ step_spatial3d(snapshot, deltas, dt) →         │   │
│  │   • Movement integration                       │   │
│  │   • Gravity application                        │   │
│  │   • Collision resolution                       │   │
│  │   • Bounds enforcement                         │   │
│  │   • SpatialAlerts emission                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Pure • Deterministic • Renderer-agnostic               │
└─────────────────────────────────────────────────────────┘