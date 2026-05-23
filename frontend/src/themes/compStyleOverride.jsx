/**
 * MUI Components whose styles are override as per theme
 * @param {JsonObject} theme Plain Json Object
 */
export function componentStyleOverrides(theme) {
    return {
        MuiButton: {
            styleOverrides: {
                root: {
                    fontWeight: 800,
                    textTransform: 'capitalize',
                    borderRadius: '999px',
                    letterSpacing: 0,
                    boxShadow: 'none'
                },
                contained: {
                    backgroundColor: '#1f2328',
                    color: '#ffffff',
                    '&:hover': {
                        backgroundColor: '#111418',
                        boxShadow: '0 16px 34px rgba(17,24,39,0.18)'
                    }
                },
                outlined: {
                    borderColor: 'rgba(17,24,39,0.18)',
                    color: '#1f2328',
                    backgroundColor: 'rgba(255,255,255,0.62)',
                    '&:hover': {
                        borderColor: '#1f2328',
                        backgroundColor: '#ffffff'
                    }
                }
            }
        },
        MuiPaper: {
            defaultProps: {
                elevation: 0
            },
            styleOverrides: {
                root: {
                    backgroundImage: 'none',
                    borderColor: 'rgba(17,24,39,0.08)'
                },
                rounded: {
                    borderRadius: '24px'
                }
            }
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: '24px',
                    border: '1px solid rgba(17,24,39,0.08)',
                    background: 'rgba(255,255,255,0.76)',
                    boxShadow: '0 24px 70px rgba(31,35,40,0.08)',
                    backdropFilter: 'blur(14px)'
                }
            }
        },
        MuiCardHeader: {
            styleOverrides: {
                root: {
                    color: theme.colors.textDark,
                    padding: '24px'
                },
                title: {
                    fontSize: '1.125rem'
                }
            }
        },
        MuiCardContent: {
            styleOverrides: {
                root: {
                    padding: '24px'
                }
            }
        },
        MuiCardActions: {
            styleOverrides: {
                root: {
                    padding: '24px'
                }
            }
        },
        MuiListItemButton: {
            styleOverrides: {
                root: {
                    color: theme.darkTextPrimary,
                    paddingTop: '10px',
                    paddingBottom: '10px',
                    borderRadius: '999px',
                    '&.Mui-selected': {
                        color: '#ffffff',
                        backgroundColor: '#1f2328',
                        '&:hover': {
                            backgroundColor: '#1f2328'
                        },
                        '& .MuiListItemIcon-root': {
                            color: '#c084fc'
                        }
                    },
                    '&:hover': {
                        backgroundColor: 'rgba(31,35,40,0.06)',
                        color: '#1f2328',
                        '& .MuiListItemIcon-root': {
                            color: '#1f2328'
                        }
                    }
                }
            }
        },
        MuiListItemIcon: {
            styleOverrides: {
                root: {
                    color: theme.darkTextPrimary,
                    minWidth: '36px'
                }
            }
        },
        MuiListItemText: {
            styleOverrides: {
                primary: {
                    color: theme.textDark
                }
            }
        },
        MuiInputBase: {
            styleOverrides: {
                input: {
                    color: theme.textDark,
                    '&::placeholder': {
                        color: theme.darkTextSecondary,
                        fontSize: '0.875rem'
                    }
                }
            }
        },
        MuiOutlinedInput: {
            styleOverrides: {
                root: {
                    background: 'rgba(255,255,255,0.78)',
                    borderRadius: '18px',
                    '& .MuiOutlinedInput-notchedOutline': {
                        borderColor: 'rgba(17,24,39,0.12)'
                    },
                    '&:hover $notchedOutline': {
                        borderColor: '#1f2328'
                    },
                    '&.MuiInputBase-multiline': {
                        padding: 1
                    }
                },
                input: {
                    fontWeight: 500,
                    background: 'transparent',
                    padding: '15.5px 14px',
                    borderRadius: '18px',
                    '&.MuiInputBase-inputSizeSmall': {
                        padding: '10px 14px',
                        '&.MuiInputBase-inputAdornedStart': {
                            paddingLeft: 0
                        }
                    }
                },
                inputAdornedStart: {
                    paddingLeft: 4
                },
                notchedOutline: {
                    borderRadius: '18px'
                }
            }
        },
        MuiSlider: {
            styleOverrides: {
                root: {
                    '&.Mui-disabled': {
                        color: theme.colors.grey300
                    }
                },
                mark: {
                    backgroundColor: theme.paper,
                    width: '4px'
                },
                valueLabel: {
                    color: theme.colors.primaryLight
                }
            }
        },
        MuiDivider: {
            styleOverrides: {
                root: {
                    borderColor: theme.divider,
                    opacity: 1
                }
            }
        },
        MuiAvatar: {
            styleOverrides: {
                root: {
                    color: theme.colors.primaryDark,
                    background: theme.colors.primary200
                }
            }
        },
        MuiChip: {
            styleOverrides: {
                root: {
                    borderRadius: '999px',
                    fontWeight: 800,
                    '&.MuiChip-deletable .MuiChip-deleteIcon': {
                        color: 'inherit'
                    }
                }
            }
        },
        MuiTooltip: {
            styleOverrides: {
                tooltip: {
                    color: theme.paper,
                    background: theme.colors.grey700
                }
            }
        }
    };
}
