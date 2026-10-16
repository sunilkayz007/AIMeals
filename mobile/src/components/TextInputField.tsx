import { useEffect, useRef, useMemo } from 'react';
import { TextInput as RNTextInput } from 'react-native';
import { Input, TextField, Label } from 'heroui-native';

/**
 * TextInputField - A controlled text input wrapper that properly handles
 * text clearing and ensures the native input state stays synchronized with
 * the React state value.
 *
 * Fixes issue where Ctrl+A + Delete would cause text to concatenate instead
 * of properly clearing by:
 * 1. Using a ref to directly manipulate the native input when needed
 * 2. Ensuring state updates properly trigger re-renders with fresh value prop
 * 3. Properly clearing the selection state after text operations
 */
interface TextInputFieldProps {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  label?: string;
  isRequired?: boolean;
  keyboardType?: 'default' | 'email-address' | 'numeric' | 'number-pad';
  secureTextEntry?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  autoCorrect?: boolean;
  editable?: boolean;
  style?: any;
  containerStyle?: any;
  maxLength?: number;
  onBlur?: () => void;
  onFocus?: () => void;
  testID?: string;
}

export const TextInputField = ({
  value,
  onChangeText,
  placeholder,
  label,
  isRequired,
  keyboardType = 'default',
  secureTextEntry = false,
  autoCapitalize = 'none',
  autoCorrect = false,
  editable = true,
  style,
  containerStyle,
  maxLength,
  onBlur,
  onFocus,
  testID,
}: TextInputFieldProps) => {
  const inputRef = useRef<RNTextInput>(null);
  const previousValueRef = useRef(value);

  /**
   * Track value changes and ensure the native input stays synchronized.
   * This prevents the text concatenation bug that occurs when the native
   * TextInput's internal buffer doesn't match the controlled value prop.
   */
  useEffect(() => {
    if (inputRef.current && previousValueRef.current !== value) {
      // Force the native input to update by setting the value directly
      // This ensures the internal buffer is cleared and synced with React state
      inputRef.current.setNativeProps({ text: value });
      previousValueRef.current = value;
    }
  }, [value]);

  /**
   * Enhanced onChangeText handler that ensures proper text handling
   * and clears selection state to prevent concatenation issues.
   */
  const handleChangeText = (text: string) => {
    // Call the provided handler (which may include filtering logic)
    onChangeText(text);

    // For empty strings (from Ctrl+A + Delete), explicitly ensure clear state
    if (text === '' && inputRef.current) {
      // Set selection to (0, 0) to clear any selection state
      if (inputRef.current.setSelection) {
        inputRef.current.setSelection(0, 0);
      }
    }
  };

  // Memoize the hasLabel check to avoid unnecessary renders
  const hasLabel = useMemo(() => !!label, [label]);

  if (hasLabel) {
    return (
      <TextField isRequired={isRequired} style={containerStyle}>
        <Label>{label}</Label>
        <Input
          ref={inputRef}
          placeholder={placeholder}
          keyboardType={keyboardType}
          secureTextEntry={secureTextEntry}
          autoCapitalize={autoCapitalize}
          autoCorrect={autoCorrect}
          editable={editable}
          value={value}
          onChangeText={handleChangeText}
          maxLength={maxLength}
          onBlur={onBlur}
          onFocus={onFocus}
          testID={testID}
          style={style}
        />
      </TextField>
    );
  }

  // Bare Input without TextField wrapper
  return (
    <Input
      ref={inputRef}
      placeholder={placeholder}
      keyboardType={keyboardType}
      secureTextEntry={secureTextEntry}
      autoCapitalize={autoCapitalize}
      autoCorrect={autoCorrect}
      editable={editable}
      value={value}
      onChangeText={handleChangeText}
      maxLength={maxLength}
      onBlur={onBlur}
      onFocus={onFocus}
      testID={testID}
      style={[containerStyle, style]}
    />
  );
};
