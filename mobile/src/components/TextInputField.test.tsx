import { render, screen, fireEvent } from '@testing-library/react-native';
import { useState } from 'react';
import { TextInputField } from './TextInputField';

/**
 * Test suite for TextInputField component
 * Verifies that the text clearing bug is fixed
 */

describe('TextInputField - Text Clearing Tests', () => {
  /**
   * Test that TextInputField properly clears text when onChangeText is called with empty string
   * This addresses the bug where Ctrl+A + Delete would cause text concatenation
   */
  it('should clear text field when onChangeText is called with empty string', () => {
    const TestComponent = () => {
      const [value, setValue] = useState('test@example.com');

      return (
        <TextInputField
          value={value}
          onChangeText={setValue}
          placeholder="Enter email"
          testID="test-input"
        />
      );
    };

    const { getByTestId, rerender } = render(<TestComponent />);
    const input = getByTestId('test-input');

    // Initial value should be set
    expect(input.props.value).toBe('test@example.com');

    // Simulate clearing the field (Ctrl+A + Delete results in empty string passed to onChangeText)
    fireEvent.changeText(input, '');

    // Re-render to reflect state update
    rerender(<TestComponent />);

    // Value should be cleared
    expect(input.props.value).toBe('');
  });

  /**
   * Test OTP field with regex filtering to ensure text doesn't concatenate
   * when Ctrl+A + Delete is pressed (text becomes empty, then regex filters it)
   */
  it('should properly handle OTP field with regex filtering on clear', () => {
    const TestComponent = () => {
      const [value, setValue] = useState('123456');

      const handleChangeText = (text: string) => {
        // Simulate the regex filter used in verify-otp.tsx
        setValue(text.replace(/[^0-9]/g, ''));
      };

      return (
        <TextInputField
          value={value}
          onChangeText={handleChangeText}
          placeholder="Enter OTP"
          keyboardType="number-pad"
          maxLength={6}
          testID="otp-input"
        />
      );
    };

    const { getByTestId, rerender } = render(<TestComponent />);
    const input = getByTestId('otp-input');

    // Initial value
    expect(input.props.value).toBe('123456');

    // Simulate Ctrl+A + Delete (empty string passed to onChangeText)
    // The regex filter: ''.replace(/[^0-9]/g, '') = ''
    fireEvent.changeText(input, '');
    rerender(<TestComponent />);

    // Value should be cleared, not concatenated
    expect(input.props.value).toBe('');
  });

  /**
   * Test that text replacement (not concatenation) happens when new text is entered
   * after clearing
   */
  it('should replace text without concatenation when new input is entered after clearing', () => {
    const TestComponent = () => {
      const [value, setValue] = useState('');

      return (
        <TextInputField
          value={value}
          onChangeText={setValue}
          placeholder="Test"
          testID="test-input"
        />
      );
    };

    const { getByTestId, rerender } = render(<TestComponent />);
    const input = getByTestId('test-input');

    // Start with empty
    expect(input.props.value).toBe('');

    // Type new text
    fireEvent.changeText(input, 'newtext');
    rerender(<TestComponent />);

    // Should be 'newtext', not concatenated with old values
    expect(input.props.value).toBe('newtext');
  });

  /**
   * Test password field clearing to ensure no buffer issues with secure entry
   */
  it('should clear password field properly with secureTextEntry', () => {
    const TestComponent = () => {
      const [value, setValue] = useState('password123!');

      return (
        <TextInputField
          value={value}
          onChangeText={setValue}
          placeholder="Password"
          secureTextEntry
          testID="password-input"
        />
      );
    };

    const { getByTestId, rerender } = render(<TestComponent />);
    const input = getByTestId('password-input');

    // Initial value
    expect(input.props.value).toBe('password123!');

    // Clear the field
    fireEvent.changeText(input, '');
    rerender(<TestComponent />);

    // Should be cleared
    expect(input.props.value).toBe('');
  });
});

/**
 * Manual Test Instructions (for QA/Developer Testing)
 *
 * 1. Run the AIMeals app on an emulator or device
 * 2. Navigate to the Sign In screen (or any auth screen with text inputs)
 * 3. Tap on the Email field
 * 4. Type an email: "test@example.com"
 * 5. Press Ctrl+A (select all) - or triple-tap and select all on mobile
 * 6. Press Delete/Backspace
 * 7. EXPECTED: Field should be completely empty
 * 8. VERIFY: No text concatenation (like "thtest@example.cpassword123!...")
 * 9. Tap the field again and type new text: "newtest@email.com"
 * 10. EXPECTED: Field should show only "newtest@email.com", not concatenated
 *
 * Repeat for:
 * - Sign Up screen (First name, Last name, Email fields)
 * - Verify OTP screen (OTP code field - uses regex filtering)
 * - Reset Password screen (OTP and Password fields)
 * - Forgot Password screen (Email field)
 */
