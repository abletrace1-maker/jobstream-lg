import logging
from src.utils.diff_applier import parse_json_path, apply_diffs

def test_parse_json_path():
    assert parse_json_path("professional_summary") == ["professional_summary"]
    assert parse_json_path("professional_experience[0].highlights[1]") == ["professional_experience", 0, "highlights", 1]
    assert parse_json_path('skills["Software Development"]') == ["skills", "Software Development"]
    assert parse_json_path("skills['Cloud-Technologies']") == ["skills", "Cloud-Technologies"]

def test_apply_diffs_valid_replace():
    base_resume = {
        "professional_summary": "Old summary",
        "professional_experience": [
            {
                "company": "Tech Corp",
                "highlights": ["Did X", "Did Y"]
            }
        ],
        "skills": {
            "languages": ["Python", "JavaScript"]
        }
    }
    
    diffs = [
        {
            "action": "replace",
            "section": "professional_summary",
            "new_value": "New summary"
        },
        {
            "action": "replace",
            "section": "professional_experience[0].highlights[1]",
            "new_value": "Did Y better"
        },
        {
            "action": "replace",
            "section": "skills.languages[0]",
            "new_value": "Go"
        }
    ]
    
    result = apply_diffs(base_resume, diffs)
    
    # Check that original is unchanged
    assert base_resume["professional_summary"] == "Old summary"
    assert base_resume["professional_experience"][0]["highlights"][1] == "Did Y"
    
    # Check that result is updated
    assert result["professional_summary"] == "New summary"
    assert result["professional_experience"][0]["highlights"][1] == "Did Y better"
    assert result["skills"]["languages"][0] == "Go"
    assert result["skills"]["languages"][1] == "JavaScript"

def test_apply_diffs_invalid_path(caplog):
    base_resume = {
        "professional_summary": "Old summary"
    }
    
    diffs = [
        {
            "action": "replace",
            "section": "invalid_section.nested",
            "new_value": "Won't work"
        },
        {
            "action": "replace",
            "section": "professional_summary[5]",
            "new_value": "Also won't work"
        }
    ]
    
    with caplog.at_level(logging.WARNING):
        result = apply_diffs(base_resume, diffs)
        
    # Original should be identical to result because diffs failed
    assert result == base_resume
    
    # Should log warnings
    assert "Failed to apply diff at path invalid_section.nested" in caplog.text
    assert "Failed to apply diff at path professional_summary[5]" in caplog.text

def test_apply_diffs_advanced_actions():
    base_resume = {
        "skills": {
            "languages": ["Python"]
        },
        "professional_experience": [
            {"company": "A"}
        ]
    }
    
    diffs = [
        {"action": "add", "section": "skills.frameworks", "new_value": ["React"]},
        {"action": "add", "section": "skills.languages", "new_value": "Go"},
        {"action": "rename", "section": "skills.frameworks", "new_value": "frontend_frameworks"},
        {"action": "remove", "section": "professional_experience[0]"},
        {"action": "add", "section": "professional_experience[0]", "new_value": {"company": "B"}}
    ]
    
    result = apply_diffs(base_resume, diffs)
    
    assert "frameworks" not in result["skills"]
    assert result["skills"]["frontend_frameworks"] == ["React"]
    assert result["skills"]["languages"] == ["Python", "Go"]
    assert len(result["professional_experience"]) == 1
    assert result["professional_experience"][0]["company"] == "B"

def test_apply_diffs_unsupported_action(caplog):
    base_resume = {
        "professional_summary": "Old summary"
    }
    
    diffs = [
        {
            "action": "unknown_action",
            "section": "professional_summary",
            "new_value": "New summary"
        }
    ]
    
    with caplog.at_level(logging.WARNING):
        result = apply_diffs(base_resume, diffs)
        
    assert result == base_resume
    assert "Unsupported action 'unknown_action'" in caplog.text
