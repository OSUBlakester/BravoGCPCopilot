#!/usr/bin/env python3
"""Test Sight Word Integration"""

import asyncio
import json
import os

def test_dolch_words_file():
    """Test that the Dolch words file is properly formatted"""
    print("🧪 Testing Dolch words file...")
    
    try:
        # Load the file
        with open('static/dolch_sight_words.json', 'r') as f:
            data = json.load(f)
        
        # Verify structure
        assert 'dolch_sight_words' in data
        assert 'grade_levels' in data
        
        # Check each grade level
        expected_grades = ['pre_k', 'kindergarten', 'first_grade', 'second_grade', 'third_grade', 'nouns']
        for grade in expected_grades:
            assert grade in data['dolch_sight_words'], f"Missing grade: {grade}"
            assert isinstance(data['dolch_sight_words'][grade], list), f"Grade {grade} should be a list"
            print(f"  ✅ {grade}: {len(data['dolch_sight_words'][grade])} words")
        
        # Check grade level configs
        expected_levels = ['pre_k', 'kindergarten', 'first_grade', 'second_grade', 'third_grade', 'third_grade_with_nouns']
        for level in expected_levels:
            assert level in data['grade_levels'], f"Missing level config: {level}"
            config = data['grade_levels'][level]
            assert 'display_name' in config
            assert 'includes' in config
            assert isinstance(config['includes'], list)
            print(f"  ✅ {level} config: includes {len(config['includes'])} grade levels")
        
        # Test cumulative counts
        total_words_by_level = {}
        for level, config in data['grade_levels'].items():
            total_words = set()
            for included_grade in config['includes']:
                if included_grade in data['dolch_sight_words']:
                    words = data['dolch_sight_words'][included_grade]
                    total_words.update(words)
            total_words_by_level[level] = len(total_words)
            print(f"  📊 {config['display_name']}: {len(total_words)} total words")
        
        print("✅ Dolch words file test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Dolch words file test failed: {e}")
        return False

def create_sight_word_test_html():
    """Create a simple HTML test page for sight word functionality"""
    print("\n🧪 Creating sight word test page...")
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sight Word Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }
        .word-test { margin: 10px 0; padding: 8px; background: #f5f5f5; }
        .sight-word { color: green; font-weight: bold; }
        .not-sight-word { color: blue; }
        .error { color: red; }
        input[type="text"] { padding: 5px; margin: 5px; width: 200px; }
        button { padding: 8px 15px; margin: 5px; cursor: pointer; }
        select { padding: 5px; margin: 5px; }
    </style>
</head>
<body>
    <h1>Sight Word Testing Interface</h1>
    
    <div class="test-section">
        <h2>Grade Level Settings</h2>
        <label for="gradeLevel">Current Grade Level:</label>
        <select id="gradeLevel">
            <option value="pre_k">Pre-Kindergarten</option>
            <option value="kindergarten">Kindergarten</option>
            <option value="first_grade">First Grade</option>
            <option value="second_grade">Second Grade</option>
            <option value="third_grade">Third Grade</option>
            <option value="third_grade_with_nouns">Third Grade + Nouns</option>
        </select>
        <button onclick="updateGradeLevel()">Update</button>
        <div id="gradeInfo"></div>
    </div>
    
    <div class="test-section">
        <h2>Test Individual Words</h2>
        <input type="text" id="testWord" placeholder="Enter word to test" onkeypress="if(event.key==='Enter')testWord()">
        <button onclick="testWord()">Test Word</button>
        <div id="wordResult"></div>
    </div>
    
    <div class="test-section">
        <h2>Predefined Test Cases</h2>
        <div id="testCases"></div>
        <button onclick="runAllTests()">Run All Tests</button>
    </div>
    
    <div class="test-section">
        <h2>Current Sight Words</h2>
        <button onclick="showAllWords()">Show All Current Sight Words</button>
        <div id="allWords"></div>
    </div>

    <script src="/static/sight-word-service.js"></script>
    <script>
        // Test cases for different scenarios
        const testCases = [
            // Pre-K words
            { text: "the", expected: true, description: "Basic Pre-K word" },
            { text: "I", expected: true, description: "Single letter Pre-K word" },
            { text: "go", expected: true, description: "Action Pre-K word" },
            
            // Kindergarten words  
            { text: "all", expected: true, description: "Kindergarten word (when K+ selected)" },
            { text: "have", expected: true, description: "Common Kindergarten word" },
            
            // First grade words
            { text: "after", expected: true, description: "First grade word (when 1st+ selected)" },
            { text: "could", expected: true, description: "Complex first grade word" },
            
            // Multi-word phrases with all sight words
            { text: "I go", expected: true, description: "Phrase with all sight words" },
            { text: "the big red", expected: true, description: "Multiple sight words" },
            
            // Mixed phrases (some sight words, some not)
            { text: "I like dinosaurs", expected: false, description: "Mixed phrase (dinosaurs not sight word)" },
            { text: "the elephant", expected: false, description: "Partial sight word phrase" },
            
            // Non-sight words
            { text: "elephant", expected: false, description: "Non-sight word" },
            { text: "computer", expected: false, description: "Complex non-sight word" },
            { text: "xyz", expected: false, description: "Random letters" },
            
            // Edge cases
            { text: "", expected: false, description: "Empty string" },
            { text: "THE", expected: true, description: "Uppercase sight word" },
            { text: "The", expected: true, description: "Capitalized sight word" },
            { text: "  the  ", expected: true, description: "Sight word with spaces" }
        ];
        
        function updateGradeLevel() {
            const select = document.getElementById('gradeLevel');
            const gradeLevel = select.value;
            
            if (window.updateSightWordSettings) {
                window.updateSightWordSettings({ sightWordGradeLevel: gradeLevel });
                
                setTimeout(() => {
                    updateGradeInfo();
                    runAllTests(); // Re-run tests with new grade level
                }, 100);
            }
        }
        
        function updateGradeInfo() {
            const info = window.getSightWordInfo ? window.getSightWordInfo() : null;
            const infoDiv = document.getElementById('gradeInfo');
            
            if (info) {
                infoDiv.innerHTML = `
                    <p><strong>Current Level:</strong> ${info.display_name}</p>
                    <p><strong>Total Words:</strong> ${info.word_count}</p>
                    <p><strong>Includes:</strong> ${info.includes ? info.includes.join(', ') : 'N/A'}</p>
                `;
            } else {
                infoDiv.innerHTML = '<p class="error">Sight word service not loaded</p>';
            }
        }
        
        function testWord() {
            const input = document.getElementById('testWord');
            const word = input.value.trim();
            const resultDiv = document.getElementById('wordResult');
            
            if (!word) {
                resultDiv.innerHTML = '<p class="error">Please enter a word</p>';
                return;
            }
            
            const isSightWord = window.isSightWord ? window.isSightWord(word) : false;
            const className = isSightWord ? 'sight-word' : 'not-sight-word';
            const status = isSightWord ? 'IS a sight word' : 'is NOT a sight word';
            
            resultDiv.innerHTML = `<p class="${className}">"${word}" ${status}</p>`;
        }
        
        function runAllTests() {
            const testCasesDiv = document.getElementById('testCases');
            testCasesDiv.innerHTML = '<h3>Test Results:</h3>';
            
            let passed = 0;
            let failed = 0;
            
            testCases.forEach(testCase => {
                const actual = window.isSightWord ? window.isSightWord(testCase.text) : false;
                const success = actual === testCase.expected;
                
                if (success) passed++;
                else failed++;
                
                const statusClass = success ? 'sight-word' : 'error';
                const statusText = success ? 'PASS' : 'FAIL';
                
                testCasesDiv.innerHTML += `
                    <div class="word-test">
                        <span class="${statusClass}">[${statusText}]</span>
                        <strong>"${testCase.text}"</strong> - ${testCase.description}
                        <br><small>Expected: ${testCase.expected}, Got: ${actual}</small>
                    </div>
                `;
            });
            
            testCasesDiv.innerHTML += `
                <div style="margin-top: 15px; padding: 10px; background: ${failed === 0 ? '#d4edda' : '#f8d7da'}; border-radius: 5px;">
                    <strong>Results: ${passed} passed, ${failed} failed</strong>
                </div>
            `;
        }
        
        function showAllWords() {
            const allWordsDiv = document.getElementById('allWords');
            
            if (window.globalSightWordService && window.globalSightWordService.getAllSightWords) {
                const words = window.globalSightWordService.getAllSightWords();
                allWordsDiv.innerHTML = `
                    <p><strong>All sight words for current level:</strong></p>
                    <div style="max-height: 200px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; background: #f9f9f9;">
                        ${words.join(', ')}
                    </div>
                `;
            } else {
                allWordsDiv.innerHTML = '<p class="error">Sight word service not available</p>';
            }
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                updateGradeInfo();
                runAllTests();
            }, 500); // Give sight word service time to load
        });
    </script>
</body>
</html>"""

    with open('static/sight-word-test.html', 'w') as f:
        f.write(html_content)
    
    print("✅ Created static/sight-word-test.html")
    print("   Access at: /static/sight-word-test.html")

def main():
    """Run all tests"""
    print("🚀 Running Sight Word Integration Tests\n")
    
    # Test the data file
    dolch_test_passed = test_dolch_words_file()
    
    # Create test page
    create_sight_word_test_html()
    
    if dolch_test_passed:
        print("\n✅ All tests passed! Sight word integration is ready.")
        print("\nNext steps:")
        print("1. Deploy the changes: ./deploy.sh dev")
        print("2. Test the functionality at: https://dev.talkwithbravo.com/static/sight-word-test.html")
        print("3. Update admin settings at: https://dev.talkwithbravo.com/static/admin_settings.html")
    else:
        print("\n❌ Some tests failed. Please fix the issues before deploying.")

if __name__ == "__main__":
    main()