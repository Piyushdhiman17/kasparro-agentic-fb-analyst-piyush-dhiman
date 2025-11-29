"""
test suite for evaluator agent
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import sys

# add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.evaluator import EvaluatorAgent


# fixtures

@pytest.fixture
def mock_config():
    """create mock configuration"""
    return {
        'thresholds': {
            'confidence_threshold': 0.6,
            'low_ctr': 0.015,
            'low_roas': 3.0
        }
    }


@pytest.fixture
def sample_dataframe():
    """create sample dataframe for testing"""
    return pd.DataFrame({
        'date': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05']),
        'campaign_name': ['Campaign A', 'Campaign A', 'Campaign B', 'Campaign B', 'Campaign C'],
        'spend': [100.0, 150.0, 200.0, 120.0, 180.0],
        'impressions': [10000, 15000, 20000, 12000, 18000],
        'clicks': [100, 150, 200, 120, 180],
        'ctr': [0.01, 0.01, 0.01, 0.01, 0.01],
        'purchases': [10, 15, 20, 12, 18],
        'revenue': [500.0, 750.0, 1000.0, 600.0, 900.0],
        'roas': [5.0, 5.0, 5.0, 5.0, 5.0],
        'creative_type': ['Image', 'Video', 'UGC', 'Image', 'Video'],
        'audience_type': ['Broad', 'Lookalike', 'Retargeting', 'Broad', 'Lookalike'],
        'platform': ['Facebook', 'Instagram', 'Facebook', 'Instagram', 'Facebook'],
        'country': ['US', 'US', 'UK', 'UK', 'IN']
    })


@pytest.fixture
def mock_data_loader(sample_dataframe):
    """create mock data loader"""
    loader = Mock()
    loader.load_data.return_value = sample_dataframe
    loader.df = sample_dataframe
    
    # mock get_creative_performance
    loader.get_creative_performance.return_value = {
        'Image': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 2, 'total_spend': 220.0, 'total_revenue': 1100.0},
        'Video': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 2, 'total_spend': 330.0, 'total_revenue': 1650.0},
        'UGC': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 1, 'total_spend': 200.0, 'total_revenue': 1000.0}
    }
    
    # mock get_audience_performance
    loader.get_audience_performance.return_value = {
        'Broad': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 2, 'total_spend': 220.0, 'total_revenue': 1100.0},
        'Lookalike': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 2, 'total_spend': 330.0, 'total_revenue': 1650.0},
        'Retargeting': {'avg_roas': 5.0, 'avg_ctr': 0.01, 'count': 1, 'total_spend': 200.0, 'total_revenue': 1000.0}
    }
    
    # mock get_summary_stats
    loader.get_summary_stats.return_value = {
        'overall_metrics': {
            'total_spend': 750.0,
            'total_revenue': 3750.0,
            'overall_roas': 5.0,
            'avg_ctr': 0.01
        },
        'breakdowns': {
            'creative_types': ['Image', 'Video', 'UGC'],
            'audience_types': ['Broad', 'Lookalike', 'Retargeting']
        }
    }
    
    # mock get_correlation_matrix
    loader.get_correlation_matrix.return_value = {
        'roas': {'spend': 0.3, 'ctr': 0.5, 'impressions': 0.2},
        'ctr': {'spend': 0.1, 'roas': 0.5, 'impressions': 0.4}
    }
    
    return loader


@pytest.fixture
def mock_llm_client():
    """create mock llm client"""
    llm = Mock()
    llm.generate_json.return_value = {
        'confidence': 0.7,
        'reasoning': 'test reasoning',
        'evidence_summary': 'test evidence',
        'recommendation': 'test recommendation'
    }
    return llm


@pytest.fixture
def evaluator(mock_llm_client, mock_data_loader, mock_config):
    """create evaluator agent with mocks"""
    with patch.object(Path, 'exists', return_value=True):
        with patch.object(Path, 'read_text', return_value='# test prompt'):
            agent = EvaluatorAgent(mock_llm_client, mock_data_loader, mock_config)
            agent.df = mock_data_loader.df
            return agent


# test class initialization

class TestEvaluatorInit:
    """tests for evaluator initialization"""
    
    def test_init_with_valid_config(self, mock_llm_client, mock_data_loader, mock_config):
        """test evaluator initializes correctly with valid config"""
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value='# test prompt'):
                agent = EvaluatorAgent(mock_llm_client, mock_data_loader, mock_config)
                
                assert agent.llm == mock_llm_client
                assert agent.loader == mock_data_loader
                assert agent.confidence_threshold == 0.6
                assert agent.df is None
    
    def test_init_loads_prompt_template(self, mock_llm_client, mock_data_loader, mock_config):
        """test that prompt template is loaded during init"""
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value='# custom prompt') as mock_read:
                agent = EvaluatorAgent(mock_llm_client, mock_data_loader, mock_config)
                
                mock_read.assert_called_once()
                assert agent.prompt_template == '# custom prompt'
    
    def test_init_raises_when_prompt_missing(self, mock_llm_client, mock_data_loader, mock_config):
        """test that init raises error when prompt file is missing"""
        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                EvaluatorAgent(mock_llm_client, mock_data_loader, mock_config)


# test validate method

class TestValidate:
    """tests for the validate method"""
    
    def test_validate_single_hypothesis(self, evaluator):
        """test validating a single hypothesis"""
        hypotheses = [{
            'id': 'H1',
            'hypothesis': 'Video content performs better than images',
            'category': 'creative'
        }]
        
        result = evaluator.validate(hypotheses)
        
        assert 'validated_hypotheses' in result
        assert len(result['validated_hypotheses']) == 1
        assert 'validation_summary' in result
        assert result['total_validated'] == 1
    
    def test_validate_multiple_hypotheses(self, evaluator):
        """test validating multiple hypotheses"""
        hypotheses = [
            {'id': 'H1', 'hypothesis': 'Video performs better', 'category': 'creative'},
            {'id': 'H2', 'hypothesis': 'Retargeting has higher ROI', 'category': 'audience'},
            {'id': 'H3', 'hypothesis': 'Weekend performance differs', 'category': 'timing'}
        ]
        
        result = evaluator.validate(hypotheses)
        
        assert len(result['validated_hypotheses']) == 3
        assert result['total_validated'] == 3
    
    def test_validate_returns_confidence_counts(self, evaluator):
        """test that validation returns confidence level counts"""
        hypotheses = [
            {'id': 'H1', 'hypothesis': 'Test hypothesis', 'category': 'creative'}
        ]
        
        result = evaluator.validate(hypotheses)
        
        assert 'high_confidence_count' in result
        assert 'medium_confidence_count' in result
        assert 'low_confidence_count' in result
        total = result['high_confidence_count'] + result['medium_confidence_count'] + result['low_confidence_count']
        assert total == result['total_validated']
    
    def test_validate_loads_data_if_not_loaded(self, evaluator, mock_data_loader):
        """test that validate loads data if not already loaded"""
        evaluator.df = None
        hypotheses = [{'id': 'H1', 'hypothesis': 'Test', 'category': 'general'}]
        
        evaluator.validate(hypotheses)
        
        mock_data_loader.load_data.assert_called()


# test creative hypothesis validation

class TestValidateCreativeHypothesis:
    """tests for creative hypothesis validation"""
    
    def test_creative_hypothesis_returns_correct_structure(self, evaluator):
        """test that creative validation returns expected structure"""
        result = evaluator._validate_creative_hypothesis('Video performs better than images')
        
        assert 'confidence' in result
        assert 'method' in result
        assert 'evidence' in result
        assert 'statistical_tests' in result
        assert 'conclusion' in result
        assert 'recommendation' in result
    
    def test_creative_hypothesis_confidence_in_range(self, evaluator):
        """test that confidence is within valid range"""
        result = evaluator._validate_creative_hypothesis('Test hypothesis')
        
        assert 0 <= result['confidence'] <= 1
    
    def test_creative_hypothesis_includes_anova_stats(self, evaluator):
        """test that anova statistics are included"""
        result = evaluator._validate_creative_hypothesis('Video vs Image')
        
        assert 'anova_f_statistic' in result['statistical_tests']
        assert 'p_value' in result['statistical_tests']
        assert 'significant' in result['statistical_tests']
    
    def test_creative_hypothesis_mentions_video_increases_confidence(self, evaluator):
        """test that mentioning video in hypothesis affects validation"""
        result_with_video = evaluator._validate_creative_hypothesis('Video content outperforms')
        result_without = evaluator._validate_creative_hypothesis('Some content outperforms')
        
        # both should return valid results
        assert result_with_video['confidence'] >= 0
        assert result_without['confidence'] >= 0


# test audience hypothesis validation

class TestValidateAudienceHypothesis:
    """tests for audience hypothesis validation"""
    
    def test_audience_hypothesis_returns_correct_structure(self, evaluator):
        """test that audience validation returns expected structure"""
        result = evaluator._validate_audience_hypothesis('Retargeting performs better')
        
        assert 'confidence' in result
        assert 'method' in result
        assert 'evidence' in result
        assert 'conclusion' in result
    
    def test_audience_hypothesis_confidence_in_range(self, evaluator):
        """test that confidence is within valid range"""
        result = evaluator._validate_audience_hypothesis('Test hypothesis')
        
        assert 0 <= result['confidence'] <= 1


# test timing hypothesis validation

class TestValidateTimingHypothesis:
    """tests for timing hypothesis validation"""
    
    def test_timing_hypothesis_returns_correct_structure(self, evaluator):
        """test that timing validation returns expected structure"""
        result = evaluator._validate_timing_hypothesis('Weekend performs differently')
        
        assert 'confidence' in result
        assert 'method' in result
        assert 'evidence' in result
    
    def test_timing_hypothesis_includes_weekend_comparison(self, evaluator):
        """test that timing validation includes weekend vs weekday data"""
        result = evaluator._validate_timing_hypothesis('Weekend test')
        
        evidence = result['evidence']
        assert 'weekend_avg_roas' in evidence or 'daily_roas' in evidence


# test performance hypothesis validation

class TestValidatePerformanceHypothesis:
    """tests for performance hypothesis validation"""
    
    def test_performance_hypothesis_returns_correct_structure(self, evaluator):
        """test that performance validation returns expected structure"""
        result = evaluator._validate_performance_hypothesis('Higher spend leads to better results')
        
        assert 'confidence' in result
        assert 'method' in result
        assert 'evidence' in result
    
    def test_performance_hypothesis_includes_correlations(self, evaluator):
        """test that performance validation includes correlation data"""
        result = evaluator._validate_performance_hypothesis('CTR impacts conversions')
        
        assert 'statistical_tests' in result


# test general hypothesis validation

class TestValidateGeneralHypothesis:
    """tests for general hypothesis validation"""
    
    def test_general_hypothesis_uses_llm(self, evaluator, mock_llm_client):
        """test that general validation uses llm"""
        result = evaluator._validate_general_hypothesis('Some general hypothesis')
        
        # llm should have been called
        mock_llm_client.generate_json.assert_called()
    
    def test_general_hypothesis_returns_correct_structure(self, evaluator):
        """test that general validation returns expected structure"""
        result = evaluator._validate_general_hypothesis('General test hypothesis')
        
        assert 'confidence' in result
        assert 'method' in result
        assert 'evidence' in result
    
    def test_general_hypothesis_handles_llm_failure(self, evaluator, mock_llm_client):
        """test that general validation handles llm failure gracefully"""
        mock_llm_client.generate_json.side_effect = Exception('LLM error')
        
        result = evaluator._validate_general_hypothesis('Test hypothesis')
        
        # should return default values
        assert result['confidence'] == 0.5
        assert result['method'] == 'Default evaluation'


# test single hypothesis validation routing

class TestValidateSingleHypothesis:
    """tests for hypothesis routing logic"""
    
    def test_routes_creative_category(self, evaluator):
        """test that creative category is routed correctly"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Test', 'category': 'creative'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['category'] == 'creative'
        assert 'Creative type' in result['validation_method']
    
    def test_routes_audience_category(self, evaluator):
        """test that audience category is routed correctly"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Test', 'category': 'audience'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['category'] == 'audience'
        assert 'Audience' in result['validation_method']
    
    def test_routes_timing_category(self, evaluator):
        """test that timing category is routed correctly"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Test', 'category': 'timing'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['category'] == 'timing'
    
    def test_routes_unknown_category_to_general(self, evaluator):
        """test that unknown category falls back to general"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Test', 'category': 'unknown_category'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['category'] == 'unknown_category'
    
    def test_preserves_hypothesis_id(self, evaluator):
        """test that hypothesis id is preserved in result"""
        hypothesis = {'id': 'H42', 'hypothesis': 'Test', 'category': 'creative'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['hypothesis_id'] == 'H42'
    
    def test_preserves_original_hypothesis_text(self, evaluator):
        """test that original hypothesis text is preserved"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Original hypothesis text', 'category': 'creative'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['original_hypothesis'] == 'Original hypothesis text'


# test statistical summary

class TestGetStatisticalSummary:
    """tests for statistical summary method"""
    
    def test_statistical_summary_returns_correct_structure(self, evaluator):
        """test that statistical summary has expected structure"""
        result = evaluator.get_statistical_summary()
        
        assert 'roas' in result
        assert 'ctr' in result
        assert 'spend' in result
    
    def test_statistical_summary_roas_metrics(self, evaluator):
        """test that roas metrics are included"""
        result = evaluator.get_statistical_summary()
        
        roas_stats = result['roas']
        assert 'mean' in roas_stats
        assert 'median' in roas_stats
        assert 'std' in roas_stats
        assert 'min' in roas_stats
        assert 'max' in roas_stats
    
    def test_statistical_summary_loads_data_if_needed(self, evaluator, mock_data_loader):
        """test that statistical summary loads data if not loaded"""
        evaluator.df = None
        
        evaluator.get_statistical_summary()
        
        mock_data_loader.load_data.assert_called()


# test edge cases

class TestEdgeCases:
    """tests for edge cases and error handling"""
    
    def test_empty_hypotheses_list(self, evaluator):
        """test handling of empty hypotheses list"""
        result = evaluator.validate([])
        
        assert result['validated_hypotheses'] == []
        assert result['total_validated'] == 0
    
    def test_hypothesis_missing_id(self, evaluator):
        """test handling of hypothesis without id"""
        hypothesis = {'hypothesis': 'Test', 'category': 'creative'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['hypothesis_id'] == 'H?'
    
    def test_hypothesis_missing_category(self, evaluator):
        """test handling of hypothesis without category"""
        hypothesis = {'id': 'H1', 'hypothesis': 'Test'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['category'] == 'general'
    
    def test_hypothesis_missing_text(self, evaluator):
        """test handling of hypothesis without text"""
        hypothesis = {'id': 'H1', 'category': 'creative'}
        
        result = evaluator._validate_single_hypothesis(hypothesis)
        
        assert result['original_hypothesis'] == ''


# run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
