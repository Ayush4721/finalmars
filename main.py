from pipeline import run_research_pipeline


def main():

    print("=" * 60)
    print("        MULTI-AGENT RESEARCH SYSTEM")
    print("=" * 60)

    while True:

        topic = input(
            "\nEnter a research topic (or 'quit'): "
        ).strip()


        if topic.lower() == "quit":

            print(
                "\nExiting research system..."
            )

            break


        if not topic:

            print(
                "Please enter a research topic."
            )

            continue


        try:

            run_research_pipeline(topic)

        except Exception as e:

            print(
                f"\nResearch pipeline failed: {e}"
            )


if __name__ == "__main__":
    main()