"""
LLM Provider factory for textcase.
"""
from typing import Dict, Optional, Any, Type
from pathlib import Path
import importlib

from textcase.core.llm.provider import LLMProvider


class LLMFactory:
    """Factory for creating LLM providers."""
    
    _providers: Dict[str, LLMProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_name: str, config_path: Path) -> LLMProvider:
        """
        Get or create a provider instance.
        
        Args:
            provider_name: Name of the provider
            config_path: Path to the provider configuration file
            
        Returns:
            LLMProvider instance
        """
        # Check if provider already exists
        if provider_name in cls._providers:
            return cls._providers[provider_name]
        
        # Load configuration
        config = LLMProvider.load_config(config_path)
        
        # Create provider based on type
        provider_type = config.get('type')
        if not provider_type:
            raise ValueError(f"Provider type not specified in configuration: {config_path}")
        
        # 按需导入 HumbugProvider
        if provider_type == 'openai' or provider_type == 'anthropic' or provider_type == 'google':
            # 动态导入 HumbugProvider
            try:
                module = importlib.import_module('textcase.core.llm.humbug_provider')
                HumbugProvider = getattr(module, 'HumbugProvider')
                provider = HumbugProvider.from_config(config)
            except ImportError as e:
                raise ImportError(f"Failed to import HumbugProvider: {e}")
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        # Cache the provider
        cls._providers[provider_name] = provider
        
        return provider
    
    @classmethod
    def get_model_providers(cls, config_dir: Path, model_name: str) -> Dict[str, LLMProvider]:
        """
        Find all providers that support a specific model.
        
        Args:
            config_dir: Directory containing provider configurations
            model_name: Name of the model to find providers for
            
        Returns:
            Dictionary mapping provider names to provider instances
        """
        result = {}
        
        # 确保配置目录存在
        if not config_dir.exists():
            return result
        
        # 遍历所有提供商配置文件
        for config_file in config_dir.glob('*.yml'):
            provider_name = config_file.stem
            
            try:
                # 加载配置
                config = LLMProvider.load_config(config_file)
                
                # 检查此提供商是否支持指定模型
                models = config.get('model', [])
                if isinstance(models, list) and model_name in models:
                    # 创建提供商实例
                    provider = cls.get_provider(provider_name, config_file)
                    result[provider_name] = provider
            except Exception as e:
                # 跳过无效配置
                print(f"Error loading provider {provider_name}: {e}")
        
        return result
