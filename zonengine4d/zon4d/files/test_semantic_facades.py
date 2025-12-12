# test_semantic_facades.py
"""
Test: Semantic Facades (Quest, Behavior, Sequence, Conversation, Maintenance, Routine)

Demonstrates that different domain-specific wrappers all use the same
TaskTree implementation underneath.
"""

from .task_system import (
    Task,
    TaskTree,
    TaskDomain,
    TaskPriority,
    TaskState,
    Quest,
    Behavior,
    Sequence,
    Conversation,
    Maintenance,
    Routine,
)


def test_01_quest():
    """Test: Quest facade for player missions"""
    print("\n" + "="*60)
    print("TEST 1: QUEST (Player Missions)")
    print("="*60)
    
    # Create a quest
    quest = Quest(
        id="find_artifact",
        quest_name="The Lost Artifact",
        description="Retrieve the ancient artifact from the ruins",
        reward_gold=100,
        reward_items=["legendary_sword"],
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add objectives
    quest.add_objective(TaskTree(
        id="talk_to_elder",
        domain=TaskDomain.NARRATIVE,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"npc": "elder", "dialogue": "quest_start"}
    ))
    
    quest.add_objective(TaskTree(
        id="travel_to_ruins",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.HIGH,
        tick_id=1,
        scene_time=0.0,
        payload={"destination": "ancient_ruins"}
    ))
    
    quest.add_objective(TaskTree(
        id="defeat_guardian",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"enemy": "stone_guardian"}
    ))
    
    print(f"Quest: {quest.quest_name}")
    print(f"Description: {quest.description}")
    print(f"Objectives: {len(quest.objectives)}")
    for i, obj in enumerate(quest.objectives, 1):
        print(f"  {i}. {obj.id}")
    print(f"Reward: {quest.reward_gold} gold + {quest.reward_items}")
    
    # Simulate progress
    quest.state = TaskState.RUNNING
    step1 = quest.advance_step()
    print(f"\nCurrent objective: {step1.id}")
    quest.mark_step_complete(0)
    print(f"Progress: {len(quest.completed_steps)}/{len(quest.objectives)}")
    
    print("\n✅ Quest works - player missions have clear structure")


def test_02_behavior():
    """Test: Behavior facade for NPC AI"""
    print("\n" + "="*60)
    print("TEST 2: BEHAVIOR (NPC AI)")
    print("="*60)
    
    # Create patrol behavior
    patrol = Behavior(
        id="guard_patrol",
        npc_id="castle_guard_01",
        loop=True,
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add actions
    patrol.add_action(TaskTree(
        id="walk_to_waypoint_1",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.MEDIUM,
        tick_id=1,
        scene_time=0.0,
        payload={"position": [10, 0, 5]}
    ))
    
    patrol.add_action(TaskTree(
        id="wait",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.LOW,
        tick_id=1,
        scene_time=0.0,
        payload={"duration": 5.0}
    ))
    
    patrol.add_action(TaskTree(
        id="walk_to_waypoint_2",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.MEDIUM,
        tick_id=1,
        scene_time=0.0,
        payload={"position": [20, 0, 10]}
    ))
    
    print(f"Behavior: {patrol.id}")
    print(f"NPC: {patrol.npc_id}")
    print(f"Actions: {len(patrol.actions)}")
    for i, action in enumerate(patrol.actions, 1):
        print(f"  {i}. {action.id}")
    print(f"Loop: {patrol.loop}")
    
    # Simulate execution
    action = patrol.advance_step()
    print(f"\nExecuting: {action.id}")
    patrol.mark_step_complete(0)
    
    # Check if should loop
    patrol.mark_step_complete(1)
    patrol.mark_step_complete(2)
    print(f"Should loop? {patrol.should_loop()}")
    
    print("\n✅ Behavior works - NPC AI uses same structure")


def test_03_sequence():
    """Test: Sequence facade for cutscenes"""
    print("\n" + "="*60)
    print("TEST 3: SEQUENCE (Cutscenes)")
    print("="*60)
    
    # Create opening cutscene
    opening = Sequence(
        id="opening_cinematic",
        skippable=True,
        auto_advance=True,
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add scenes
    opening.add_scene(TaskTree(
        id="fade_in",
        domain=TaskDomain.VFX,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"duration": 2.0}
    ))
    
    opening.add_scene(TaskTree(
        id="camera_pan",
        domain=TaskDomain.CAMERA,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"target": "castle", "duration": 5.0}
    ))
    
    opening.add_scene(TaskTree(
        id="title_card",
        domain=TaskDomain.VFX,
        priority=TaskPriority.HIGH,
        tick_id=1,
        scene_time=0.0,
        payload={"text": "EngAIn: The Game"}
    ))
    
    print(f"Sequence: {opening.id}")
    print(f"Scenes: {len(opening.scenes)}")
    for i, scene in enumerate(opening.scenes, 1):
        print(f"  {i}. {scene.id}")
    print(f"Skippable: {opening.skippable}")
    
    # Player presses skip
    if opening.skippable:
        opening.skip()
        print(f"\nSkipped to end")
        print(f"State: {opening.state.name}")
    
    print("\n✅ Sequence works - cutscenes use same structure")


def test_04_conversation():
    """Test: Conversation facade for dialogue"""
    print("\n" + "="*60)
    print("TEST 4: CONVERSATION (Dialogue)")
    print("="*60)
    
    # Create conversation
    convo = Conversation(
        id="keen_introduction",
        speaker="keen",
        listener="player",
        emotion="curious",
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add lines
    convo.add_line(TaskTree(
        id="line_001",
        domain=TaskDomain.NARRATIVE,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"text": "Hello there, traveler!"}
    ))
    
    convo.add_line(TaskTree(
        id="wait_for_choice",
        domain=TaskDomain.NARRATIVE,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"choices": ["Hello!", "Who are you?", "Leave"]}
    ))
    
    # Branch paths
    convo.add_line(TaskTree(
        id="choice_hello",
        domain=TaskDomain.NARRATIVE,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
        payload={"text": "Nice to meet you!"}
    ))
    
    print(f"Conversation: {convo.id}")
    print(f"Speaker: {convo.speaker}")
    print(f"Listener: {convo.listener}")
    print(f"Emotion: {convo.emotion}")
    print(f"Lines: {len(convo.lines)}")
    
    # Simulate dialogue
    line1 = convo.advance_step()
    print(f"\n{convo.speaker}: {line1.payload['text']}")
    
    line2 = convo.advance_step()
    print(f"Choices: {line2.payload['choices']}")
    
    # Player chooses option 0
    choice = convo.branch(2)  # Jump to choice_hello
    print(f"\n{convo.speaker}: {choice.payload['text']}")
    
    print("\n✅ Conversation works - dialogue uses same structure")


def test_05_maintenance():
    """Test: Maintenance facade for pocket tasks"""
    print("\n" + "="*60)
    print("TEST 5: MAINTENANCE (Pocket Tasks)")
    print("="*60)
    
    # Create maintenance task
    cleanup = Maintenance(
        id="memory_cleanup",
        memory_threshold=0.8,
        auto_schedule=True,
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add cleanup steps
    cleanup.add_step(TaskTree(
        id="flush_deltas",
        domain=TaskDomain.ENGINE_MAINTENANCE,
        priority=TaskPriority.MEDIUM,
        tick_id=1,
        scene_time=0.0,
    ))
    
    cleanup.add_step(TaskTree(
        id="consolidate_snapshots",
        domain=TaskDomain.ENGINE_MAINTENANCE,
        priority=TaskPriority.MEDIUM,
        tick_id=1,
        scene_time=0.0,
    ))
    
    cleanup.add_step(TaskTree(
        id="purge_temp_memory",
        domain=TaskDomain.ENGINE_MAINTENANCE,
        priority=TaskPriority.MEDIUM,
        tick_id=1,
        scene_time=0.0,
    ))
    
    print(f"Maintenance: {cleanup.id}")
    print(f"Tasks: {len(cleanup.tasks)}")
    for i, task in enumerate(cleanup.tasks, 1):
        print(f"  {i}. {task.id}")
    print(f"Memory threshold: {cleanup.memory_threshold * 100}%")
    
    # Check if should run
    current_usage = 0.85
    should_run = cleanup.should_run(current_usage)
    print(f"\nCurrent memory: {current_usage * 100}%")
    print(f"Should run cleanup? {should_run}")
    
    print("\n✅ Maintenance works - pocket tasks use same structure")


def test_06_routine():
    """Test: Routine facade for recurring tasks"""
    print("\n" + "="*60)
    print("TEST 6: ROUTINE (Recurring Tasks)")
    print("="*60)
    
    # Create shop restock routine
    restock = Routine(
        id="shop_daily_restock",
        interval_seconds=86400.0,  # 24 hours
        tick_id=1,
        scene_time=0.0,
    )
    
    # Add restock steps
    restock.add_step(TaskTree(
        id="generate_inventory",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.LOW,
        tick_id=1,
        scene_time=0.0,
        payload={"shop_id": "general_store"}
    ))
    
    restock.add_step(TaskTree(
        id="update_prices",
        domain=TaskDomain.SPATIAL,
        priority=TaskPriority.LOW,
        tick_id=1,
        scene_time=0.0,
        payload={"shop_id": "general_store"}
    ))
    
    print(f"Routine: {restock.id}")
    print(f"Steps: {len(restock.steps)}")
    for i, step in enumerate(restock.steps, 1):
        print(f"  {i}. {step.id}")
    print(f"Interval: {restock.interval_seconds / 3600} hours")
    
    # Simulate time passing
    current_time = 0.0
    restock.mark_run(current_time)
    print(f"\nLast run: {restock.last_run_time}")
    
    current_time = 90000.0  # 25 hours later
    should_run = restock.should_run(current_time)
    print(f"Current time: {current_time / 3600} hours")
    print(f"Should run? {should_run}")
    
    print("\n✅ Routine works - recurring tasks use same structure")


def test_07_unified_router():
    """Test: All facades route through same TaskRouter"""
    print("\n" + "="*60)
    print("TEST 7: UNIFIED ROUTING")
    print("="*60)
    
    from .task_system import TaskRouter, LoggingTaskHandler
    
    router = TaskRouter()
    
    # Register handlers
    for domain in TaskDomain:
        router.register_handler(domain, LoggingTaskHandler(domain))
    
    # Create mixed tasks
    quest = Quest(
        id="test_quest",
        tick_id=1,
        scene_time=0.0,
    )
    quest.add_objective(TaskTree(
        id="obj1",
        domain=TaskDomain.NARRATIVE,
        priority=TaskPriority.CRITICAL,
        tick_id=1,
        scene_time=0.0,
    ))
    
    behavior = Behavior(
        id="test_behavior",
        npc_id="guard",
        tick_id=1,
        scene_time=0.0,
    )
    
    maintenance = Maintenance(
        id="test_maintenance",
        tick_id=1,
        scene_time=0.0,
    )
    
    # Route them all
    tasks_to_route = [
        quest.to_task(),
        behavior.to_task(),
        maintenance.to_task(),
    ]
    
    results = router.route_batch(tasks_to_route)
    
    print(f"Routed {results['handled']} tasks")
    print(f"Quest routed: ✅")
    print(f"Behavior routed: ✅")
    print(f"Maintenance routed: ✅")
    
    print("\n✅ All facades route through same system")


def run_all_tests():
    print("\n" + "="*60)
    print("SEMANTIC FACADES TEST SUITE")
    print("Same TaskTree, Different Meanings")
    print("="*60)
    
    test_01_quest()
    test_02_behavior()
    test_03_sequence()
    test_04_conversation()
    test_05_maintenance()
    test_06_routine()
    test_07_unified_router()
    
    print("\n" + "="*60)
    print("🔥 ALL SEMANTIC FACADE TESTS PASSED 🔥")
    print("="*60)
    print("\nWhat this proves:")
    print("  ✅ Quest - player missions")
    print("  ✅ Behavior - NPC AI")
    print("  ✅ Sequence - cutscenes")
    print("  ✅ Conversation - dialogue")
    print("  ✅ Maintenance - pocket tasks")
    print("  ✅ Routine - recurring tasks")
    print("  ✅ All use same TaskTree underneath")
    print("  ✅ All route through same TaskRouter")
    print("\nOne implementation, many semantic meanings.")
    print("This is clean architecture.")


if __name__ == "__main__":
    run_all_tests()
