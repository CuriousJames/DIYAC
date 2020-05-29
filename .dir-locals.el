;; The 'nil' configuration applies to all modes.
    ((nil . ((indent-tabs-mode . t)
            (tab-width . 1)))

(add-hook 'python-mode-hook 'guess-style-guess-tabs-mode)	
(add-hook 'python-mode-hook (lambda ()	
	(guess-style-guess-tab-width)))
	
