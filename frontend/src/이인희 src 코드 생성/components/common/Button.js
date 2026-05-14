import styled from 'styled-components';
import palette from './이인희 src 코드 생성/lib/styles/palette';

const StyledButton = styled.button`
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: bold;
    padding: 0.25rem 1rem;
    color: white;
    outline: none;
    cursor: pointer;

    background: ${palette.blue[8]};
    &:hover {
        background: ${palette.blue[6]};
    }
`;

const Button = props => <StyledButton {...props} />;

export default Button