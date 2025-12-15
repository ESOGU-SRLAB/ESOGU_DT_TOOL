// This file contains the processes data for the testing automation tool.
// Each process includes an ID, name, details, inputs, and output.
export const processes = [
  {
    id: 'code-review',
    name: 'Code Review',
    details: [
      'Performs automated code review using LLMs with support for multiple programming languages.',
      'Evaluates code quality based on readability, maintainability, performance, and best practices.',
      'Identifies bugs, anti-patterns, and refactoring opportunities with contextual justifications.',
      'Provides educational feedback for developers with varying experience levels.',
      'Suggests actionable improvements and alternative implementations where applicable.',
      'Supports multiple programming languages and frameworks.',
    ],
    inputs: [],
    output: 'Code Review Report'
  },  
  {
    id: 'requirement-analysis',
    name: 'Requirement Analysis',
    details: [
      'Reviews and analyzes project requirements and specifications in depth to ensure clarity and completeness.',
      'Identifies testable requirements, acceptance criteria, and potential ambiguities or inconsistencies.',
      'Highlights missing, conflicting, or unclear requirements and provides actionable feedback.',
      'Ensures alignment between business goals, user needs, and technical specifications.',
      'Facilitates communication between stakeholders, developers, and testers for shared understanding.',
      'Supports iterative refinement of requirements throughout the project lifecycle.'
    ],
    inputs: ['Requirement Document', 'Technical Design Document'],
    output: 'Requirements Analysis Report'
  },
  {
    id: 'test-planning',
    name: 'Test Planning',
    details: [
      'Develops a comprehensive test strategy and plan tailored to the project scope and objectives.',
      'Defines test objectives, scope, approach, and deliverables in detail.',
      'Estimates required resources, timelines, and creates a detailed test schedule.',
      'Identifies risks, dependencies, and mitigation strategies for the testing process.',
      'Specifies entry and exit criteria, test environment needs, and tool requirements.',
      'Coordinates with stakeholders to ensure test plan alignment with project goals.',
      'Establishes communication and reporting protocols for test progress and issues.'
    ],
    inputs: ['Requirements Analysis Report', 'Code Review Report'],
    output: 'Test Plan'
  },
  {
    id: 'environment-setup',
    name: 'Environment Setup',
    details: [
      'Identifies the required programming language, framework, and operating system for the project (e.g., Python >=3.9, Flask, Ubuntu 20.04).',
      'Lists all necessary dependencies (such as Flask, requests, gunicorn) and their versions, and provides installation instructions.',
      'Specifies database requirements and additional tools needed (e.g., pip, virtualenv).',
      'Provides step-by-step setup instructions and highlights important considerations for the environment.',
      'Offers guidance on common installation issues and troubleshooting tips.',
      'Recommends best practices for configuring and optimizing the development and deployment environment.',
      'Encourages removal of unnecessary dependencies and tools to ensure a clean and secure setup.'
    ],
    inputs: ['Test Scripts', 'Technical Design Document'],
    output: 'Environment Setup Report'
  },
  {
    id: 'test-scenario-generation',
    name: 'Test Scenario Generation',
    details: [
      'Generate comprehensive test scenarios based on input documents',
      'Supports multiple testing types and advanced configuration',
      'AI-powered scenario generation with customizable parameters',
      {
        title: 'Supported Test Types',
        type: 'table',
        data: [
          {
            testType: 'Performance and Load Testing',
            category: 'Non-Functional',
            methodology: 'Simulate user activity patterns'
          },
          {
            testType: 'Integration Testing',
            category: 'Functional',
            methodology: 'Define interactions between connected modules'
          },
          {
            testType: 'Input Data Variety Testing',
            category: 'Functional',
            methodology: 'Explore inputs with diverse attributes and formats'
          },
          {
            testType: 'Functional Testing',
            category: 'Functional',
            methodology: 'Cover required functionalities comprehensively'
          },
          {
            testType: 'Edge Cases and Boundary Testing',
            category: 'Functional',
            methodology: 'Test limits and unexpected scenarios'
          },
          {
            testType: 'Compatibility Testing',
            category: 'Non-Functional',
            methodology: 'Ensure adaptability across environments'
          },
          {
            testType: 'User Interface (GUI) Testing',
            category: 'Functional',
            methodology: 'Focus on usability and responsiveness'
          },
          {
            testType: 'Security Testing',
            category: 'Non-Functional',
            methodology: 'Identify and address potential vulnerabilities intelligently'
          }
        ]
      }
    ],
    inputs: [
      'Source Code',
      'Test Plan',
      'Technical Design Document',
      'Requirements Document'
    ],
    defaultPrompt: 'Generate test scenarios considering the provided input and selected test type.'
  },
  {
    id: 'test-case-generation',
    name: 'Test Case Generation',
    details: [
      'Develop detailed test cases based on optimized scenarios',
      'Ensure test cases align with user requirements',
      'Validate test cases for completeness and accuracy'
    ],
    inputs: ['Optimized Test Scenarios', 'Requirements Analysis Report'],
    output: 'Test Cases'
  },
  {
    id: 'test-case-optimization',
    name: 'Test Case Optimization',
    details: [
      'Review and optimize test cases for maximum coverage',
      'Eliminate duplicate test cases and redundancies',
      'Ensure test case effectiveness and efficiency'
    ],
    inputs: ['Test Cases'],
    output: 'Optimized Test Cases'
  },
  {
    id: 'test-code-generation',
    name: 'Test Code Generation',
    details: [
      'Generate executable test code from unique test cases and source code',
      'Automatically detect programming language and recommend appropriate test framework',
      'Use environment setup results to ensure generated tests are compatible with the target environment',
      'Create framework-specific test codes (pytest, unittest, jest, junit, etc.)',
      'Generate one test code per unique test case for comprehensive coverage',
      'Ensure generated test codes are ready to run without modifications',
      'Support multiple programming languages (Python, JavaScript, Java, C#, etc.)'
    ],
    inputs: ['Unique Test Cases', 'Source Code', 'Environment Setup Results'],
    output: 'Executable Test Code Files',
    defaultPrompt: 'Generate executable test code based on unique test cases, source code analysis, and environment setup configuration.'
  },
 
  {
    id: 'test-execution',
    name: 'Test Execution',
    details: [
      'Execute generated test code using AI providers (LM Studio or Gemini)',
      'View test code in an integrated Monaco Editor with syntax highlighting',
      'Run tests through Model Context Protocol (MCP) server for reliable execution',
      'Monitor real-time execution results in a terminal-like interface',
      'Switch between different AI providers seamlessly',
      'Track execution history and performance metrics',
      'Support for multiple programming languages and test frameworks'
    ],
    inputs: ['Generated Test Code', 'AI Provider Configuration'],
    output: 'Test Execution Results'
  },
  {
    id: 'test-reporting',
    name: 'Test Reporting',
    details: [
      'Generate comprehensive reports from STLC process data',
      'AI-powered analysis with smart chunking for large datasets',
      'Supports multi-process analysis and synthesis',
      'Provides executive summaries and detailed insights',
      'Includes metrics, trends, and actionable recommendations',
      'Flexible reporting with configurable analysis depth'
    ],
    inputs: ['Session Data', 'Selected Processes'],
    output: 'Comprehensive Test Report'
  },
  {
    id: 'test-closure',
    name: 'Test Closure',
    details: [
      'Generate AI-powered test cycle closure reports analyzing all STLC phases',
      'Aggregate metrics from test scenarios, cases, execution, and defects',
      'Calculate pass rates, coverage metrics, and optimization effectiveness',
      'Provide executive summaries with quality assessment and recommendations',
      'Identify lessons learned and areas for improvement in future cycles',
      'Include comprehensive defect analysis and risk assessment',
      'Generate actionable recommendations for stakeholders',
      'Support multi-session analysis for complete project closure'
    ],
    inputs: ['Test Sessions', 'Test Execution Results', 'All STLC Process Data'],
    output: 'AI-Generated Test Closure Report',
    defaultPrompt: 'Generate a comprehensive test closure report with metrics, quality assessment, and recommendations.'
  }
];