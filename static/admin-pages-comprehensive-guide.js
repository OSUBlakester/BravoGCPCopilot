/**
 * Comprehensive Interactive Guide for Admin Pages
 * Combines structured tour, Smart Help AI, and multimedia content
 */

class AdminPagesComprehensiveGuide {
    constructor() {
        this.currentStep = 0;
        this.isActive = false;
        this.smartHelp = null; // Will be initialized later
        this.multimedia = null; // Will be initialized later
        this.overlay = null;
        this.guidePanel = null;
        this.userProgress = this.loadProgress();
        
        // Initialize the guide system when dependencies are ready
        this.initializeWhenReady();
    }

    initializeWhenReady() {
        // Wait for SmartHelpSystem and MultimediaHelpSystem to be available
        let retryCount = 0;
        const maxRetries = 100; // 10 seconds max wait time
        
        const checkDependencies = () => {
            console.log(`Checking dependencies, attempt ${retryCount + 1}`);
            
            if (typeof SmartHelpSystem !== 'undefined' && typeof MultimediaHelpSystem !== 'undefined') {
                console.log('Dependencies found, initializing comprehensive guide...');
                try {
                    this.smartHelp = new SmartHelpSystem();
                    this.multimedia = new MultimediaHelpSystem();
                    this.initializeGuide();
                    console.log('Comprehensive guide initialized successfully');
                } catch (error) {
                    console.error('Error initializing comprehensive guide:', error);
                }
            } else {
                retryCount++;
                if (retryCount < maxRetries) {
                    console.log(`Dependencies not ready (SmartHelpSystem: ${typeof SmartHelpSystem}, MultimediaHelpSystem: ${typeof MultimediaHelpSystem}), retrying...`);
                    setTimeout(checkDependencies, 100);
                } else {
                    console.error('Failed to initialize comprehensive guide after maximum retries');
                }
            }
        };
        
        // Start checking immediately, but also wait for DOMContentLoaded if needed
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', checkDependencies);
        } else {
            checkDependencies();
        }
    }

    initializeGuide() {
        console.log('Initializing comprehensive guide...');
        
        // Note: Using existing help button instead of creating new one
        // this.createHelpButton();
        
        // Create guide overlay and panel
        this.createGuideOverlay();
        this.createGuidePanel();
        
        // Initialize Smart Help and Multimedia systems
        this.smartHelp.initialize();
        this.multimedia.initialize();
        
        // Add event listeners
        this.addEventListeners();
        
        console.log('Comprehensive guide initialization complete');
    }

    createHelpButton() {
        // Using existing help button in admin_pages.html instead of creating new one
        return;
        
        /* Original button creation code commented out
        const helpButton = document.createElement('button');
        helpButton.id = 'comprehensive-help-btn';
        helpButton.innerHTML = '🎯 Comprehensive Guide';
        helpButton.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
        `;
        
        helpButton.addEventListener('mouseenter', () => {
            helpButton.style.transform = 'translateY(-2px)';
            helpButton.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
        });
        
        helpButton.addEventListener('mouseleave', () => {
            helpButton.style.transform = 'translateY(0)';
            helpButton.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
        });
        
        helpButton.addEventListener('click', () => this.startComprehensiveGuide());
        
        document.body.appendChild(helpButton);
        */
    }

    createGuideOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.id = 'comprehensive-guide-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 15000;
            display: none;
            backdrop-filter: blur(3px);
        `;
        document.body.appendChild(this.overlay);
    }

    createGuidePanel() {
        this.guidePanel = document.createElement('div');
        this.guidePanel.id = 'comprehensive-guide-panel';
        this.guidePanel.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            z-index: 15001;
            display: none;
            overflow: hidden;
        `;
        
        this.guidePanel.innerHTML = `
            <div id="guide-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 22px;">Adding a New Button — Guide</h2>
                <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">Step-by-step walkthrough for the Add New Button wizard</p>
            </div>
            
            <div id="guide-content" style="padding: 30px; overflow-y: auto; max-height: 60vh;">
                <!-- Dynamic content will be loaded here -->
            </div>
            
            <div id="guide-footer" style="background: #f8f9fa; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e9ecef;">
                <div id="guide-progress" style="display: flex; align-items: center;">
                    <div id="progress-bar" style="width: 200px; height: 8px; background: #e9ecef; border-radius: 4px; margin-right: 15px;">
                        <div id="progress-fill" style="height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px; width: 0%; transition: width 0.3s ease;"></div>
                    </div>
                    <span id="progress-text" style="font-size: 14px; color: #6c757d;">Step 0 of 0</span>
                </div>
                
                <div id="guide-controls" style="display: flex; gap: 10px;">
                    <button id="guide-prev" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Previous</button>
                    <button id="guide-next" style="background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Next</button>
                    <button id="guide-close" style="background: #dc3545; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.guidePanel);
    }

    getGuideSteps() {
        return [
            {
                title: "Adding a New Button",
                type: "overview",
                content: `
                    <div style="text-align: center; margin-bottom: 24px;">
                        <div style="font-size: 40px; margin-bottom: 12px;">➕</div>
                        <h3 style="margin: 0 0 8px;">Adding a New Button</h3>
                        <p style="font-size: 15px; color: #6c757d; line-height: 1.6; margin: 0;">
                            There are two ways to add a button to a page. This guide walks you through both paths.
                        </p>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 20px 0;">
                        <div style="background: #eff6ff; border: 2px solid #3b82f6; padding: 16px; border-radius: 10px;">
                            <strong style="color: #1d4ed8;">Button Wizard</strong>
                            <p style="font-size: 13px; color: #374151; margin: 8px 0 0;">
                                Bravo guides you through creating a button step-by-step with AI suggestions for label and speech text.
                            </p>
                        </div>
                        <div style="background: #f0fdf4; border: 2px solid #22c55e; padding: 16px; border-radius: 10px;">
                            <strong style="color: #15803d;">Create Manually</strong>
                            <p style="font-size: 13px; color: #374151; margin: 8px 0 0;">
                                Opens the button editor directly so you can fill in all fields yourself with full control.
                            </p>
                        </div>
                    </div>

                    <div style="background: #fff7ed; border-left: 4px solid #f97316; padding: 14px; border-radius: 8px; margin: 16px 0;">
                        <strong style="color: #c2410c;">Before you start:</strong>
                        <p style="font-size: 13px; color: #374151; margin: 6px 0 0;">
                            Make sure you have the correct page selected in the <strong>Manage Pages &amp; Buttons</strong> tab.
                            Buttons are always added to the currently selected page.
                        </p>
                    </div>

                    <p style="color: #6b7280; font-size: 13px; text-align: center; margin: 8px 0 0;">
                        Click <strong>Next</strong> to walk through the full process step by step.
                    </p>
                `,
                smartHelpContext: "add_button_overview"
            },
            {
                title: "Step 1 — Click Add New Button",
                type: "hands_on",
                highlightTarget: "#addNewButtonBtn",
                content: `
                    <h3 style="margin-top: 0;">Click the "Add New Button" button</h3>
                    <p style="color: #374151;">In the <strong>Page Buttons</strong> section, locate the green <strong>Add New Button</strong> button at the top of the button list.</p>

                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin: 16px 0; display: flex; align-items: center; gap: 12px;">
                        <div style="background: #16a34a; color: white; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; white-space: nowrap;">
                            ＋ Add New Button
                        </div>
                        <span style="font-size: 13px; color: #6b7280;">Click this to open the two-step placement wizard.</span>
                    </div>

                    <p style="font-size: 13px; color: #374151;">This opens a small modal with two steps:</p>
                    <ol style="font-size: 13px; color: #374151; line-height: 1.8;">
                        <li><strong>Step 1:</strong> Choose where to place the new button in the list</li>
                        <li><strong>Step 2:</strong> Choose how to create it — wizard or manually</li>
                    </ol>

                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 8px; margin: 14px 0;">
                        <strong style="color: #1e40af; font-size: 13px;">The highlighted element above</strong>
                        <p style="font-size: 13px; color: #374151; margin: 4px 0 0;">
                            The blue outline shows exactly which button to click on the page behind this guide.
                        </p>
                    </div>
                `,
                smartHelpContext: "add_button_step1"
            },
            {
                title: "Step 1 — Choose Placement",
                type: "hands_on",
                highlightTarget: "#anbStep1",
                content: `
                    <h3 style="margin-top: 0;">Choose where to place the button</h3>
                    <p style="font-size: 13px; color: #374151;">After clicking <strong>Add New Button</strong>, the wizard shows a placement list. Select one option:</p>

                    <div style="margin: 16px 0;">
                        <div style="background: #f0fdf4; border: 1px solid #86efac; padding: 12px; border-radius: 8px; margin: 8px 0;">
                            <strong style="color: #15803d; font-size: 13px;">End of list (default)</strong>
                            <p style="font-size: 12px; color: #374151; margin: 4px 0 0;">The new button is added after all existing buttons. This is the most common choice.</p>
                        </div>
                        <div style="background: #fefce8; border: 1px solid #fde047; padding: 12px; border-radius: 8px; margin: 8px 0;">
                            <strong style="color: #854d0e; font-size: 13px;">Top of list</strong>
                            <p style="font-size: 12px; color: #374151; margin: 4px 0 0;">The new button becomes the first button — it will appear in the first row on the scan interface.</p>
                        </div>
                        <div style="background: #faf5ff; border: 1px solid #d8b4fe; padding: 12px; border-radius: 8px; margin: 8px 0;">
                            <strong style="color: #6b21a8; font-size: 13px;">Before [existing button name]</strong>
                            <p style="font-size: 12px; color: #374151; margin: 4px 0 0;">The list shows each existing button with a "Before …" option. Pick one to insert the new button just ahead of it.</p>
                        </div>
                    </div>

                    <p style="font-size: 13px; color: #6b7280;">
                        Once you've selected a position, click <strong>Next →</strong> to move to Step 2.
                    </p>
                `,
                smartHelpContext: "add_button_placement"
            },
            {
                title: "Step 2 — Choose Creation Method",
                type: "hands_on",
                highlightTarget: "#anbStep2",
                content: `
                    <h3 style="margin-top: 0;">Choose how to create the button</h3>
                    <p style="font-size: 13px; color: #374151;">Step 2 asks how you'd like to build the button. Pick the method that suits you:</p>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 16px 0;">
                        <div style="background: #eff6ff; border: 2px solid #3b82f6; padding: 16px; border-radius: 10px;">
                            <div style="font-size: 22px; margin-bottom: 6px;">🪄</div>
                            <strong style="color: #1d4ed8; display: block; margin-bottom: 6px;">Button Wizard</strong>
                            <p style="font-size: 12px; color: #374151; margin: 0;">
                                Bravo walks you through a guided setup. It suggests button labels and speech text based on the page context.
                                Great when you want AI-assisted suggestions.
                            </p>
                        </div>
                        <div style="background: #f0fdf4; border: 2px solid #22c55e; padding: 16px; border-radius: 10px;">
                            <div style="font-size: 22px; margin-bottom: 6px;">✏️</div>
                            <strong style="color: #15803d; display: block; margin-bottom: 6px;">Create Manually</strong>
                            <p style="font-size: 12px; color: #374151; margin: 0;">
                                Opens the button editor immediately. You fill in all fields yourself.
                                Best when you already know exactly what the button should say or do.
                            </p>
                        </div>
                    </div>

                    <div style="background: #fff7ed; border-left: 4px solid #f97316; padding: 12px; border-radius: 8px; margin: 14px 0;">
                        <strong style="color: #c2410c; font-size: 13px;">Tip:</strong>
                        <p style="font-size: 13px; color: #374151; margin: 4px 0 0;">
                            Not sure which to pick? Start with the <strong>Button Wizard</strong> — you can always edit the result afterward.
                        </p>
                    </div>
                `,
                smartHelpContext: "add_button_method"
            },
            {
                title: "Path A — Button Wizard",
                type: "hands_on",
                highlightTarget: "#helpWizardModal",
                content: `
                    <h3 style="margin-top: 0;">Using the Button Wizard</h3>
                    <p style="font-size: 13px; color: #374151;">When you choose <strong>Button Wizard</strong>, the Bravo wizard opens and guides you through each field.</p>

                    <div style="margin: 16px 0;">
                        <div style="display: flex; align-items: flex-start; gap: 10px; padding: 10px; border-radius: 8px; background: #f9fafb; margin: 8px 0;">
                            <div style="background: #3b82f6; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;">1</div>
                            <div>
                                <strong style="font-size: 13px;">Button Label</strong>
                                <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">The text that appears on the button. Keep it short and clear.</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: flex-start; gap: 10px; padding: 10px; border-radius: 8px; background: #f9fafb; margin: 8px 0;">
                            <div style="background: #3b82f6; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;">2</div>
                            <div>
                                <strong style="font-size: 13px;">Button Type</strong>
                                <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">Static (fixed phrase), AI Dynamic (context-aware response), or Navigation (links to another page).</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: flex-start; gap: 10px; padding: 10px; border-radius: 8px; background: #f9fafb; margin: 8px 0;">
                            <div style="background: #3b82f6; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;">3</div>
                            <div>
                                <strong style="font-size: 13px;">Content / Target</strong>
                                <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">The phrase to speak, the AI prompt, or the page to navigate to — depending on button type.</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: flex-start; gap: 10px; padding: 10px; border-radius: 8px; background: #f9fafb; margin: 8px 0;">
                            <div style="background: #3b82f6; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;">4</div>
                            <div>
                                <strong style="font-size: 13px;">Confirm &amp; Accept</strong>
                                <p style="font-size: 12px; color: #6b7280; margin: 2px 0 0;">Review the summary and click <strong>Accept</strong>. The button is added to the list at the position you chose.</p>
                            </div>
                        </div>
                    </div>

                    <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 8px; margin: 14px 0;">
                        <strong style="color: #991b1b; font-size: 13px;">Remember to save!</strong>
                        <p style="font-size: 13px; color: #374151; margin: 4px 0 0;">
                            After the wizard closes, click <strong>Save Button Changes</strong> to persist the new button.
                        </p>
                    </div>
                `,
                smartHelpContext: "add_button_wizard"
            },
            {
                title: "Path B — Create Manually",
                type: "hands_on",
                highlightTarget: "#buttonEditorModal",
                content: `
                    <h3 style="margin-top: 0;">Using the Button Editor</h3>
                    <p style="font-size: 13px; color: #374151;">When you choose <strong>Create Manually</strong>, the button editor opens directly. Fill in the fields for your button:</p>

                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin: 14px 0;">
                        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 8px 10px 8px 0; font-weight: 600; white-space: nowrap; vertical-align: top;">Label</td>
                                <td style="padding: 8px 0; color: #374151;">Text shown on the button. Required.</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 8px 10px 8px 0; font-weight: 600; white-space: nowrap; vertical-align: top;">Speech Text</td>
                                <td style="padding: 8px 0; color: #374151;">What Bravo says aloud when the button is pressed. Defaults to the label if left blank.</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 8px 10px 8px 0; font-weight: 600; white-space: nowrap; vertical-align: top;">AI Query</td>
                                <td style="padding: 8px 0; color: #374151;">Enter a prompt here to make this a dynamic AI button. Leave blank for a static button.</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 8px 10px 8px 0; font-weight: 600; white-space: nowrap; vertical-align: top;">Target Page</td>
                                <td style="padding: 8px 0; color: #374151;">Select a page to make this a navigation button. Leave blank otherwise.</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 10px 0 0; font-weight: 600; white-space: nowrap; vertical-align: top;">Hidden</td>
                                <td style="padding: 8px 0 0; color: #374151;">Check to hide this button from the user's scan interface. It stays in the admin list with a dashed border.</td>
                            </tr>
                        </table>
                    </div>

                    <p style="font-size: 13px; color: #374151;">Click <strong>Save</strong> in the editor to add the button. Then click <strong>Save Button Changes</strong> to persist all changes to the page.</p>
                `,
                smartHelpContext: "add_button_manual"
            },
            {
                title: "Button Indicators",
                type: "reference",
                content: `
                    <h3 style="margin-top: 0;">Reading button indicators in the list</h3>
                    <p style="font-size: 13px; color: #374151;">Each button in the Page Buttons list has a colored left border and badge that shows its type at a glance:</p>

                    <div style="margin: 16px 0;">
                        <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background: #faf5ff; border: 1px solid #d8b4fe; border-left: 4px solid #7c3aed; border-radius: 8px; margin: 8px 0;">
                            <span style="background: #7c3aed; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; white-space: nowrap;">AI</span>
                            <div>
                                <strong style="font-size: 13px; color: #6d28d9;">AI Dynamic Button</strong>
                                <p style="font-size: 12px; color: #374151; margin: 2px 0 0;">Has an AI Query — Bravo generates a context-aware response each time it's pressed.</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background: #fff7ed; border: 1px solid #fed7aa; border-left: 4px solid #f97316; border-radius: 8px; margin: 8px 0;">
                            <span style="background: #f97316; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; white-space: nowrap;">→</span>
                            <div>
                                <strong style="font-size: 13px; color: #c2410c;">Navigation Button</strong>
                                <p style="font-size: 12px; color: #374151; margin: 2px 0 0;">Linked to a Target Page — pressing it takes the user to that page.</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #16a34a; border-radius: 8px; margin: 8px 0;">
                            <span style="background: #16a34a; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; white-space: nowrap;">♪</span>
                            <div>
                                <strong style="font-size: 13px; color: #15803d;">Speech Button</strong>
                                <p style="font-size: 12px; color: #374151; margin: 2px 0 0;">Has a custom Speech Text that differs from the label.</p>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background: #f3f4f6; border: 1px dashed #9ca3af; border-left: 4px dashed #9ca3af; border-radius: 8px; margin: 8px 0; opacity: 0.8;">
                            <span style="background: #f3f4f6; color: #6b7280; border: 1px solid #d1d5db; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; white-space: nowrap;">👁 Hidden</span>
                            <div>
                                <strong style="font-size: 13px; color: #4b5563;">Hidden Button</strong>
                                <p style="font-size: 12px; color: #374151; margin: 2px 0 0;">Not visible to users. Shown here with a dashed border and reduced opacity. Does not take up a visible slot in the scan interface rows.</p>
                            </div>
                        </div>
                    </div>
                `,
                smartHelpContext: "button_indicators"
            },
            {
                title: "Row Dividers & Buttons Per Row",
                type: "reference",
                content: `
                    <h3 style="margin-top: 0;">Understanding row dividers</h3>
                    <p style="font-size: 13px; color: #374151;">The Page Buttons list shows <strong>Row 1</strong>, <strong>Row 2</strong>, etc. dividers so you can see exactly how buttons will be grouped on the scan interface.</p>

                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin: 14px 0; font-size: 12px; color: #374151;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                            <div style="flex:1; height:1px; background:#d1d5db;"></div>
                            <span style="text-transform: uppercase; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; color: #9ca3af;">Row 1</span>
                            <div style="flex:1; height:1px; background:#d1d5db;"></div>
                        </div>
                        <p style="margin: 0; color: #6b7280;">↑ This divider appears every N visible buttons, where N is your <strong>Buttons Per Row</strong> setting.</p>
                    </div>

                    <div style="background: #fff7ed; border-left: 4px solid #f97316; padding: 12px; border-radius: 8px; margin: 14px 0;">
                        <strong style="color: #c2410c; font-size: 13px;">Hidden buttons don't count toward row fill</strong>
                        <p style="font-size: 13px; color: #374151; margin: 4px 0 0;">
                            A hidden button is skipped on the scan interface, so it doesn't use up a visible row slot.
                            If you have 8 buttons per row and one is hidden, there will be 9 entries in the list before the next row divider.
                        </p>
                    </div>

                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 8px; margin: 14px 0;">
                        <strong style="color: #1e40af; font-size: 13px;">Changing Buttons Per Row</strong>
                        <p style="font-size: 13px; color: #374151; margin: 4px 0 0;">
                            Find the orange <strong>Buttons Per Row</strong> card just above the Page Buttons list.
                            Change the number and click <strong>Save</strong> — the dividers update immediately.
                            This is a global setting that applies to all pages.
                        </p>
                    </div>
                `,
                smartHelpContext: "row_dividers"
            },
            {
                title: "Done — Save Your Changes",
                type: "completion",
                content: `
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="font-size: 40px; margin-bottom: 10px;">✅</div>
                        <h3 style="margin: 0 0 8px;">You're ready to add buttons!</h3>
                        <p style="font-size: 14px; color: #6c757d; line-height: 1.6; margin: 0;">
                            Here's a quick recap of the full flow.
                        </p>
                    </div>

                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; margin: 16px 0;">
                        <ol style="font-size: 13px; color: #374151; line-height: 2; margin: 0; padding-left: 20px;">
                            <li>Select the page you want to add a button to</li>
                            <li>Click <strong>Add New Button</strong></li>
                            <li>Choose a placement position, then click <strong>Next →</strong></li>
                            <li>Choose <strong>Button Wizard</strong> or <strong>Create Manually</strong></li>
                            <li>Complete the wizard or fill in the editor fields</li>
                            <li>Click <strong>Save Button Changes</strong> to persist everything</li>
                        </ol>
                    </div>

                    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 14px; text-align: center; margin: 16px 0;">
                        <strong style="color: #991b1b; font-size: 14px;">Always click Save Button Changes when you're done!</strong>
                        <p style="font-size: 12px; color: #374151; margin: 6px 0 0;">Changes to the button list are not saved automatically.</p>
                    </div>

                    <div style="text-align: center; margin-top: 16px;">
                        <p style="font-size: 13px; color: #6b7280;">
                            You can also use <strong>Use Bravo to Create Static Buttons</strong> to generate an entire set of buttons for a page at once — useful for new pages.
                        </p>
                    </div>
                `,
                smartHelpContext: "completion_next_steps"
            }
        ];
    }

    startComprehensiveGuide() {
        // Check if the guide is fully initialized
        if (!this.smartHelp || !this.multimedia) {
            console.warn('Guide system not fully initialized yet, please try again in a moment');
            return;
        }
        
        this.currentStep = 0;
        this.isActive = true;
        this.overlay.style.display = 'block';
        this.guidePanel.style.display = 'block';
        this.showCurrentStep();
        this.saveProgress();
        
        // Initialize Smart Help context
        if (this.smartHelp?.setContext) this.smartHelp.setContext('comprehensive_guide_started');
    }

    showCurrentStep() {
        const steps = this.getGuideSteps();
        const step = steps[this.currentStep];
        
        if (!step) return;
        
        // Update content
        const contentEl = document.getElementById('guide-content');
        contentEl.innerHTML = step.content;
        
        // Update progress
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const progress = ((this.currentStep + 1) / steps.length) * 100;
        
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `Step ${this.currentStep + 1} of ${steps.length}`;
        
        // Update controls
        const prevBtn = document.getElementById('guide-prev');
        const nextBtn = document.getElementById('guide-next');
        
        prevBtn.disabled = this.currentStep === 0;
        nextBtn.textContent = this.currentStep === steps.length - 1 ? 'Complete' : 'Next';
        
        // Highlight target if specified
        this.clearHighlights();
        if (step.highlightTarget) {
            this.highlightElement(step.highlightTarget);
        }
        
        // Set Smart Help context
        if (step.smartHelpContext && this.smartHelp?.setContext) {
            this.smartHelp.setContext(step.smartHelpContext);
        }
        
        // Auto-scroll to top of content
        contentEl.scrollTop = 0;
        
        this.saveProgress();
    }

    highlightElement(selector) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            if (el) {
                el.style.outline = '3px solid #667eea';
                el.style.outlineOffset = '4px';
                el.style.borderRadius = '8px';
                el.style.position = 'relative';
                el.style.zIndex = '14999';
                
                // Add pulsing animation
                const pulse = document.createElement('div');
                pulse.className = 'guide-pulse-animation';
                pulse.style.cssText = `
                    position: absolute;
                    top: -10px;
                    left: -10px;
                    right: -10px;
                    bottom: -10px;
                    border: 2px solid #667eea;
                    border-radius: 12px;
                    animation: guidePulse 2s infinite;
                    pointer-events: none;
                    z-index: 14998;
                `;
                
                el.style.position = 'relative';
                el.appendChild(pulse);
            }
        });
        
        // Add CSS animation if not exists
        if (!document.getElementById('guide-pulse-styles')) {
            const styles = document.createElement('style');
            styles.id = 'guide-pulse-styles';
            styles.textContent = `
                @keyframes guidePulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.05); }
                    100% { opacity: 1; transform: scale(1); }
                }
            `;
            document.head.appendChild(styles);
        }
    }

    clearHighlights() {
        // Remove outlines
        document.querySelectorAll('[style*="outline"]').forEach(el => {
            el.style.outline = '';
            el.style.outlineOffset = '';
        });
        
        // Remove pulse animations
        document.querySelectorAll('.guide-pulse-animation').forEach(el => {
            el.remove();
        });
    }

    addEventListeners() {
        // Navigation controls
        document.getElementById('guide-prev').addEventListener('click', () => {
            if (this.currentStep > 0) {
                this.currentStep--;
                this.showCurrentStep();
            }
        });
        
        document.getElementById('guide-next').addEventListener('click', () => {
            const steps = this.getGuideSteps();
            if (this.currentStep < steps.length - 1) {
                this.currentStep++;
                this.showCurrentStep();
            } else {
                this.completeGuide();
            }
        });
        
        document.getElementById('guide-close').addEventListener('click', () => {
            this.closeGuide();
        });
        
        // Close on overlay click
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.closeGuide();
            }
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.isActive) return;
            
            if (e.key === 'Escape') {
                this.closeGuide();
            } else if (e.key === 'ArrowLeft' && this.currentStep > 0) {
                this.currentStep--;
                this.showCurrentStep();
            } else if (e.key === 'ArrowRight') {
                const steps = this.getGuideSteps();
                if (this.currentStep < steps.length - 1) {
                    this.currentStep++;
                    this.showCurrentStep();
                } else {
                    this.completeGuide();
                }
            }
        });
    }

    closeGuide() {
        this.isActive = false;
        this.overlay.style.display = 'none';
        this.guidePanel.style.display = 'none';
        this.clearHighlights();
        this.saveProgress();
    }

    completeGuide() {
        this.userProgress.completed = true;
        this.userProgress.completedAt = new Date().toISOString();
        this.saveProgress();
        
        // Show completion celebration
        this.smartHelp.celebrateCompletion();
        
        // Close after a moment
        setTimeout(() => {
            this.closeGuide();
        }, 2000);
    }

    startPracticeExercise(type) {
        this.multimedia.startPracticeExercise(type);
    }

    downloadGuideReference() {
        // Create downloadable reference guide
        const referenceContent = this.generateReferenceGuide();
        const blob = new Blob([referenceContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'admin-pages-reference-guide.html';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateReferenceGuide() {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Admin Pages Reference Guide</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    h1, h2, h3 { color: #667eea; }
                    .tip { background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 15px 0; }
                    .warning { background: #fff3cd; border-left: 4px solid #ffc107; }
                    .success { background: #d4edda; border-left: 4px solid #28a745; }
                </style>
            </head>
            <body>
                <h1>🎯 Admin Pages Reference Guide</h1>
                <p>Quick reference for managing pages and buttons in your AAC system.</p>
                
                <h2>📄 Page Management</h2>
                <div class="tip">
                    <strong>Creating Pages:</strong> Always start with a clear purpose and organize by communication topics.
                </div>
                
                <h2>🔘 Button Design</h2>
                <div class="tip">
                    <strong>Design Principles:</strong> Use clear icons, readable text, and appropriate colors for maximum usability.
                </div>
                
                <h2>🧭 Navigation Setup</h2>
                <div class="tip">
                    <strong>Best Practice:</strong> Create logical hierarchies and provide easy back/home navigation options.
                </div>
                
                <h2>🤖 Smart Help</h2>
                <div class="success">
                    Smart Help AI is always available for contextual assistance and personalized recommendations.
                </div>
                
                <p><em>Generated on ${new Date().toLocaleDateString()}</em></p>
            </body>
            </html>
        `;
    }

    saveProgress() {
        const progress = {
            currentStep: this.currentStep,
            completed: this.userProgress.completed || false,
            lastAccessed: new Date().toISOString(),
            completedAt: this.userProgress.completedAt || null
        };
        localStorage.setItem('adminPagesGuideProgress', JSON.stringify(progress));
    }

    loadProgress() {
        const saved = localStorage.getItem('adminPagesGuideProgress');
        return saved ? JSON.parse(saved) : { currentStep: 0, completed: false };
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.guideInstance = new AdminPagesComprehensiveGuide();
});

// Export for global access
window.AdminPagesComprehensiveGuide = AdminPagesComprehensiveGuide;
