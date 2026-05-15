from agents.router.router import TaskRouter

router = TaskRouter()

def run_test(text):
    result = router.route(text)
    print(f"INPUT: {text}")
    print(f"OUTPUT: {result}")
    print("-" * 40)

tests = [
    "напиши python код для парсинга",
    "найди информацию про qdrant",
    "запомни это правило",
    "привет как дела",
]

for t in tests:
    run_test(t)
