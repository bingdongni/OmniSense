# Contributing to OmniSense

Thank you for your interest in contributing to OmniSense! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

- Report bugs and issues
- Suggest new features
- Add support for new platforms
- Improve documentation
- Fix bugs and submit pull requests
- Improve test coverage
- Help with translations

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/omnisense.git
cd omnisense

# Add upstream remote
git remote add upstream https://github.com/bingdongni/omnisense.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Install Playwright browsers
playwright install chromium
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## 📝 Development Guidelines

### Code Style

We follow PEP 8 guidelines. Use these tools:

```bash
# Format code
black omnisense/

# Check style
flake8 omnisense/

# Type checking
mypy omnisense/

# Sort imports
isort omnisense/
```

### Writing Tests

All new features should include tests:

```python
# tests/test_your_feature.py
import pytest
from omnisense import YourFeature

def test_your_feature():
    feature = YourFeature()
    result = feature.do_something()
    assert result == expected_value
```

Run tests:

```bash
pytest tests/
pytest --cov=omnisense tests/  # With coverage
```

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    More detailed description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong

    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

### Commit Messages

Follow conventional commits:

```
feat: add support for Instagram platform
fix: resolve proxy pool connection issue
docs: update API documentation
test: add tests for sentiment analysis
refactor: improve spider manager performance
style: format code with black
chore: update dependencies
```

## 🔧 Adding a New Platform

To add support for a new platform:

### 1. Create Platform Module

```bash
cp omnisense/spider/platforms/_template.py omnisense/spider/platforms/newplatform.py
```

### 2. Implement Required Methods

```python
class NewPlatformSpider(BasePlatformSpider):
    """Spider for NewPlatform"""

    def __init__(self):
        super().__init__(platform="newplatform")

    async def search_by_keyword(self, keyword: str, max_count: int) -> List[Dict]:
        # Implement keyword search
        pass

    async def get_user_content(self, user_id: str, max_count: int) -> List[Dict]:
        # Implement user content collection
        pass

    # Implement other required methods...
```

### 3. Add Anti-Crawl Measures

```python
# In omnisense/anti_crawl/platforms/newplatform.py
class NewPlatformAntiCrawl(AntiCrawlHandler):
    def setup_fingerprint(self):
        # Platform-specific fingerprint
        pass
```

### 4. Add Tests

```python
# tests/test_platforms/test_newplatform.py
@pytest.mark.asyncio
async def test_newplatform_search():
    spider = NewPlatformSpider()
    results = await spider.search_by_keyword("test", max_count=10)
    assert len(results) > 0
```

### 5. Update Documentation

- Add platform to `docs/platforms/newplatform.md`
- Update README.md platform list
- Add usage examples

## 📋 Pull Request Process

### 1. Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts with main

### 2. Submit PR

1. Push to your fork
2. Create pull request on GitHub
3. Fill out PR template
4. Link related issues
5. Request review

### 3. PR Review

Maintainers will review your PR and may:
- Request changes
- Ask questions
- Suggest improvements
- Approve and merge

### 4. After Merge

- Delete your branch
- Update your fork
- Celebrate! 🎉

## 🐛 Reporting Bugs

Use the [GitHub issue tracker](https://github.com/bingdongni/omnisense/issues).

Include:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Code samples

**Template:**

```markdown
**Environment:**
- OS: Windows 11
- Python: 3.11.5
- OmniSense: 1.0.0

**Description:**
Brief description of the bug

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Logs:**
```
Error logs here
```

## 💡 Feature Requests

We welcome feature suggestions!

Include:
- Clear description
- Use cases
- Why it's valuable
- Possible implementation approach

## 🎁 Contributor Rewards

Core contributors receive:
- 🏆 Name in README contributors section
- 💎 Free Pro subscription (worth ¥2999/year)
- 📚 Technical books and swag
- ✨ Write access to repository
- 📢 Feature in blog/social media

## 📞 Questions?

- GitHub Discussions: [Link]
- Email: bingdongni@example.com
- Discord: [Link]

## 📜 Code of Conduct

Be respectful and inclusive. We're building a welcoming community.

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to OmniSense! 🙏
