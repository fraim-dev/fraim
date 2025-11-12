import { useState } from 'react'

export const GitHubSecretsSetup = () => {
  const [prUrl, setPrUrl] = useState('')
  const [error, setError] = useState('')

  const parsePrUrl = () => {
    if (!prUrl.trim()) {
      setError('Please enter a pull request URL')
      return null
    }

    try {
      // Parse the GitHub PR URL to extract owner/org and repo
      const url = new URL(prUrl.trim())
      
      if (url.hostname !== 'github.com') {
        setError('Please enter a valid GitHub pull request URL')
        return null
      }

      // Extract the path and get the owner and repo
      const pathParts = url.pathname.split('/').filter(part => part.length > 0)
      
      if (pathParts.length < 4 || pathParts[2] !== 'pull') {
        setError('Invalid PR URL format. Expected: https://github.com/owner/repo/pull/123')
        return null
      }

      return {
        owner: pathParts[0],
        repo: pathParts[1],
        prNumber: pathParts[3]
      }
    } catch (err) {
      setError('Invalid URL format. Please enter a valid GitHub pull request URL.')
      return null
    }
  }

  const openSecretsPage = () => {
    setError('')
    
    const parsed = parsePrUrl()
    if (!parsed) return

    // Generate the repository secrets URL
    const secretsUrl = `https://github.com/${parsed.owner}/${parsed.repo}/settings/secrets/actions`
    
    // Open the GitHub repository secrets page
    window.open(secretsUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="p-6 border dark:border-zinc-700 rounded-lg not-prose bg-zinc-50 dark:bg-zinc-900">
      <h4 className="text-lg font-semibold mb-4 text-zinc-900 dark:text-zinc-100">
        Setup GitHub Secrets
      </h4>

      <div className="mb-6 text-sm text-zinc-600 dark:text-zinc-400">
        <p className="mb-4"><strong>Required Secrets:</strong> You'll need to add these secrets to your repository:</p>
        <ul className="list-disc list-inside space-y-2 ml-4">
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">ANTHROPIC_API_KEY</code> - Your Anthropic API key for LLM processing</li>
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">GH_TOKEN</code> - Personal Access Token with repo and pull_requests permissions</li>
        </ul>
        <p className="mt-4 text-xs">
          <strong>Note:</strong> For the Risk Flagger workflow, the GH_TOKEN is required because the default GitHub Actions token doesn't have permissions to create status checks or request reviewers.
        </p>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">
            Pull Request URL
          </label>
          <input
            type="url"
            value={prUrl}
            onChange={(e) => setPrUrl(e.target.value)}
            placeholder="https://github.com/your-org/your-repo/pull/123"
            className="w-full px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 dark:bg-zinc-800 dark:text-zinc-100"
          />
          {error && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </div>

        <div className="mt-6">
          <button
            onClick={openSecretsPage}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            Open Repository Secrets
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
        </div>

        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <h5 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
            Setup Instructions:
          </h5>
          <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
            <li>Click the button above to open your repository's secrets page</li>
            <li>Add <code className="text-xs bg-blue-100 dark:bg-blue-800 px-1 rounded">ANTHROPIC_API_KEY</code> with your Anthropic API key</li>
            <li>Add <code className="text-xs bg-blue-100 dark:bg-blue-800 px-1 rounded">GH_TOKEN</code> with your Personal Access Token</li>
            <li>Save both secrets and you're ready to use Fraim GitHub Actions!</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
