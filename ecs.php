<?php

use PhpCsFixer\Fixer\ClassNotation\OrderedClassElementsFixer;
use PhpCsFixer\Fixer\ControlStructure\NoUnneededControlParenthesesFixer;
use PhpCsFixer\Fixer\LanguageConstruct\FunctionToConstantFixer;
use Symplify\EasyCodingStandard\Config\ECSConfig;
use Symplify\EasyCodingStandard\ValueObject\Set\SetList;

return static function (ECSConfig $ecsConfig): void {
    $ecsConfig->paths([
        __DIR__ . '/src',
        __DIR__ . '/tests',
    ]);

    $ecsConfig->sets([
        SetList::CONTROL_STRUCTURES,
        SetList::CLEAN_CODE,
        SetList::PSR_12,
    ]);

    $ecsConfig->skip([
        NoUnneededControlParenthesesFixer::class,
        OrderedClassElementsFixer::class,
        FunctionToConstantFixer::class,
    ]);
};
