#!/usr/bin/env python3
"""
Test script for casual conversation filter
Tests various message types to ensure proper classification
"""

from casual_conversation_filter import is_casual_message, get_casual_response
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_casual_filter():
    """Test the casual conversation filter with various inputs"""

    # Test cases: (message, expected_category_or_none, description)
    test_cases = [
        # Greetings
        ("hello", "greetings", "Simple greeting"),
        ("Hello!", "greetings", "Greeting with exclamation"),
        ("Hi there", "greetings", "Informal greeting"),
        ("Good morning", "greetings", "Time-based greeting"),
        ("Hey", "greetings", "Casual greeting"),
        ("what's up", "greetings", "Casual what's up"),

        # Thanks
        ("thank you", "thanks", "Simple thanks"),
        ("Thanks!", "thanks", "Thanks with exclamation"),
        ("thank u", "thanks", "Abbreviated thanks"),
        ("appreciate it", "thanks", "Alternative thanks"),
        ("thanks a lot", "thanks", "Extended thanks"),

        # Farewells
        ("goodbye", "farewells", "Simple goodbye"),
        ("bye", "farewells", "Short goodbye"),
        ("see you later", "farewells", "See you later"),
        ("take care", "farewells", "Take care"),
        ("good night", "farewells", "Good night"),

        # Acknowledgments
        ("ok", "acknowledgments", "Simple OK"),
        ("okay", "acknowledgments", "Okay spelling"),
        ("sure", "acknowledgments", "Sure response"),
        ("got it", "acknowledgments", "Got it"),
        ("sounds good", "acknowledgments", "Sounds good"),
        ("yes", "acknowledgments", "Yes response"),
        ("no", "acknowledgments", "No response"),

        # Capability questions
        ("what can you do", "capability_questions", "What can you do"),
        ("how can you help", "capability_questions", "How can you help"),
        ("tell me about yourself", "capability_questions", "Tell me about yourself"),
        ("what are your capabilities", "capability_questions", "Capabilities question"),

        # Casual chat
        ("how are you", "casual_chat", "How are you"),
        ("how're you doing", "casual_chat", "How are you doing"),
        ("nice to meet you", "casual_chat", "Nice to meet you"),

        # NON-CASUAL (should return None) - Document-related questions
        ("What does the document say about sales?", None, "Document question"),
        ("Find information about quarterly reports",
         None, "Document search request"),
        ("Summarize the methodology section", None, "Document summarization"),
        ("What are the main points in chapter 3?", None, "Content analysis"),
        ("Can you extract the financial data?", None, "Data extraction"),
        ("Compare these two documents", None, "Document comparison"),
        ("hello, can you tell me about the sales report?",
         None, "Mixed greeting + document question"),
        ("I need to find specific information about pricing",
         None, "Information request"),
        ("Show me all mentions of artificial intelligence", None, "Search query"),
        ("What's the conclusion of the research paper?", None, "Research question"),

        # Edge cases
        ("", None, "Empty string"),
        ("   ", None, "Whitespace only"),
        ("HELLO", "greetings", "All caps greeting"),
        ("thank you very much for your help!", "thanks", "Long thanks"),
        ("hi, how can you help me find documents about AI?",
         None, "Greeting + document question"),
    ]

    print("=" * 80)
    print("CASUAL CONVERSATION FILTER TEST")
    print("=" * 80)

    passed = 0
    failed = 0

    for message, expected_category, description in test_cases:
        result = is_casual_message(message)

        # Check if result matches expectation
        success = (result == expected_category)
        status = "✅ PASS" if success else "❌ FAIL"

        print(
            f"{status} | '{message}' -> {result} | Expected: {expected_category} | {description}")

        if success:
            passed += 1
            # If it's casual, test the response generation
            if result:
                response = get_casual_response(result)
                print(
                    f"      Response: {response[:80]}{'...' if len(response) > 80 else ''}")
        else:
            failed += 1

        print()

    print("=" * 80)
    print(
        f"TEST RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"Success rate: {(passed / (passed + failed) * 100):.1f}%")
    print("=" * 80)

    if failed == 0:
        print("🎉 ALL TESTS PASSED! The casual conversation filter is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the filter patterns.")

    return failed == 0


def test_response_generation():
    """Test response generation for different categories"""
    print("\n" + "=" * 80)
    print("RESPONSE GENERATION TEST")
    print("=" * 80)

    categories = ['greetings', 'thanks', 'farewells',
                  'acknowledgments', 'capability_questions', 'casual_chat']

    for category in categories:
        print(f"\n--- {category.upper()} ---")

        # Test without chatbot description
        response = get_casual_response(category)
        print(f"Default: {response}")

        # Test with chatbot description
        response_with_desc = get_casual_response(
            category, "financial analysis and investment research")
        print(f"With desc: {response_with_desc}")


def benchmark_performance():
    """Benchmark the performance of casual message detection"""
    import time

    print("\n" + "=" * 80)
    print("PERFORMANCE BENCHMARK")
    print("=" * 80)

    test_messages = [
        "hello",
        "thank you",
        "What does the document say about quarterly sales?",
        "how are you",
        "bye",
        "Find information about artificial intelligence in the research papers"
    ]

    iterations = 1000

    for message in test_messages:
        start_time = time.time()

        for _ in range(iterations):
            result = is_casual_message(message)

        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds
        avg_time = total_time / iterations

        print(f"'{message}' -> {result}")
        print(
            f"  {iterations} iterations: {total_time:.2f}ms total, {avg_time:.4f}ms average")
        print()


if __name__ == "__main__":
    print("🧪 Testing Casual Conversation Filter...")

    # Run main tests
    all_passed = test_casual_filter()

    # Test response generation
    test_response_generation()

    # Performance benchmark
    benchmark_performance()

    if all_passed:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
